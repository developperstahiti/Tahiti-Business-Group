"""Moteur de synchronisation petites-annonces.pf → TBG.

Approche choisie :
- Un compte TBG distinct est créé pour chaque vendeur unique (matché par téléphone normalisé)
- Mot de passe inutilisable, is_imported=True → le vrai vendeur pourra revendiquer
- Photos téléchargées sans limite, converties en WebP via image_utils.save_webp
- Mise à jour incrémentale du PASyncRun après chaque annonce → progression temps réel
  visible sur le dashboard
"""
import io
import logging
import re
from urllib.parse import urlparse

from django.contrib.auth import get_user_model
from django.utils import timezone

from ads.models import Annonce, PASyncRun
from ads.image_utils import save_webp
from ads.scrapers import petitesannonces_pf as pa
from ads.scrapers.category_mapper import IMMOBILIER_CATEGORIES, map_pa_category

logger = logging.getLogger(__name__)
User = get_user_model()


# ──────────────────────────────────────────────────────────────────
#  Helpers vendeurs : 1 compte TBG par téléphone unique
# ──────────────────────────────────────────────────────────────────
def _normalize_phone(phone):
    """Garde uniquement les chiffres et conserve les 8 derniers (Tahiti = 8 chiffres)."""
    if not phone:
        return ''
    digits = re.sub(r'\D', '', phone)
    if len(digits) >= 8:
        return digits[-8:]
    return digits


def get_or_create_seller_user(name, phone, email):
    """Récupère (ou crée) un compte vendeur TBG matché par téléphone normalisé.

    Le téléphone est la clé primaire de dédup. Si pas de téléphone, on tente l'email.
    Si rien des deux, on crée un compte avec un email synthétique unique par annonce.
    """
    norm_phone = _normalize_phone(phone)
    cleaned_name = (name or '').strip()[:150] or 'Vendeur'

    # 1. Match par téléphone (méthode principale)
    if norm_phone:
        synthetic_email = f'pa-{norm_phone}@tbg.local'
        user = User.objects.filter(email=synthetic_email).first()
        if user:
            # Met à jour le nom si on a mieux
            if cleaned_name and (not user.nom or len(cleaned_name) > len(user.nom)):
                user.nom = cleaned_name
                user.save(update_fields=['nom'])
            return user, False
        # Crée
        user = User.objects.create(
            email=synthetic_email,
            nom=cleaned_name,
            tel=phone or '',
            is_active=True,
            is_imported=True,
            email_verified=False,  # le vrai vendeur devra confirmer
        )
        user.set_unusable_password()
        user.save(update_fields=['password'])
        return user, True

    # 2. Fallback : match par email réel
    if email:
        clean_email = email.strip().lower()
        user = User.objects.filter(email__iexact=clean_email).first()
        if user:
            return user, False
        user = User.objects.create(
            email=clean_email,
            nom=cleaned_name,
            is_active=True,
            is_imported=True,
            email_verified=False,
        )
        user.set_unusable_password()
        user.save(update_fields=['password'])
        return user, True

    # 3. Dernier recours : compte anonyme par hash
    import hashlib
    h = hashlib.sha1(cleaned_name.encode('utf-8', errors='ignore')).hexdigest()[:8]
    synthetic_email = f'pa-anon-{h}@tbg.local'
    user, created = User.objects.get_or_create(
        email=synthetic_email,
        defaults={
            'nom': cleaned_name,
            'is_active': True,
            'is_imported': True,
            'email_verified': False,
        },
    )
    if created:
        user.set_unusable_password()
        user.save(update_fields=['password'])
    return user, created


# ──────────────────────────────────────────────────────────────────
#  Sync principal
# ──────────────────────────────────────────────────────────────────
def sync_immobilier(limit=None, dry_run=False, skip_photos=False, only_cat=None,
                    triggered_by=None):
    """Synchronise toutes les sous-catégories immobilier de PA.

    Args:
        limit        : max d'annonces à traiter par catégorie (None = toutes)
        dry_run      : si True, ne crée/modifie rien en DB
        skip_photos  : si True, ne télécharge pas les photos
        only_cat     : si fourni (int), traite uniquement cette catégorie PA
        triggered_by : User qui a lancé (None = cron)

    Retourne un dict de stats : created, updated, archived, errors, skipped, photos_downloaded
    """
    stats = {
        'created':  0,
        'updated':  0,
        'archived': 0,
        'errors':   0,
        'skipped':  0,
        'photos_downloaded': 0,
        'users_created':     0,
    }
    error_messages = []
    seen_ad_ids = set()

    cats_to_process = [only_cat] if only_cat else IMMOBILIER_CATEGORIES

    run = None
    if not dry_run:
        run = PASyncRun.objects.create(triggered_by=triggered_by, status='running')

    for c_id in cats_to_process:
        mapping = map_pa_category(c_id)
        if not mapping:
            continue
        categorie, sous_cat, transaction = mapping

        try:
            items = pa.fetch_rss(c_id)
        except Exception as e:
            err = f'fetch_rss c={c_id} : {type(e).__name__}: {e}'
            logger.error(f'[SYNC] {err}')
            error_messages.append(err)
            stats['errors'] += 1
            _save_run_progress(run, stats, error_messages)
            continue

        if limit:
            items = items[:limit]

        for item in items:
            ad_id = item['ad_id']
            seen_ad_ids.add(ad_id)
            try:
                result = _process_item(
                    item, categorie, sous_cat, transaction,
                    dry_run=dry_run, skip_photos=skip_photos, stats=stats,
                )
                stats[result] = stats.get(result, 0) + 1
            except Exception as e:
                err = f'process ad_id={ad_id} : {type(e).__name__}: {e}'
                logger.exception(f'[SYNC] {err}')
                error_messages.append(err)
                stats['errors'] += 1
            finally:
                # Update DB après CHAQUE annonce → progression temps réel
                _save_run_progress(run, stats, error_messages)
                pa.polite_sleep()

        logger.info(
            f'[SYNC] c={c_id} terminé. Créés={stats["created"]} '
            f'Maj={stats["updated"]} Skip={stats["skipped"]}'
        )

    if not dry_run:
        archived = _archive_missing(seen_ad_ids, only_cat)
        stats['archived'] = archived

    if run:
        run.finished_at = timezone.now()
        run.status = 'success' if stats['errors'] == 0 else 'error'
        run.nb_created  = stats['created']
        run.nb_updated  = stats['updated']
        run.nb_archived = stats['archived']
        run.nb_skipped  = stats['skipped']
        run.nb_errors   = stats['errors']
        run.nb_photos   = stats['photos_downloaded']
        run.error_msg   = '\n'.join(error_messages[:30])
        run.save()

    return stats


def _save_run_progress(run, stats, error_messages):
    """Met à jour le PASyncRun en cours de route → permet la progression temps réel."""
    if not run:
        return
    run.nb_created  = stats['created']
    run.nb_updated  = stats['updated']
    run.nb_skipped  = stats['skipped']
    run.nb_errors   = stats['errors']
    run.nb_photos   = stats['photos_downloaded']
    if error_messages:
        run.error_msg = '\n'.join(error_messages[:30])
    run.save(update_fields=[
        'nb_created', 'nb_updated', 'nb_skipped', 'nb_errors', 'nb_photos', 'error_msg',
    ])


def _process_item(item, categorie, sous_cat, transaction, *,
                  dry_run, skip_photos, stats):
    """Traite une annonce du RSS. Retourne 'created', 'updated' ou 'skipped'."""
    ad_id = item['ad_id']
    existing = Annonce.objects.filter(external_pa_id=ad_id).first()

    try:
        detail = pa.fetch_detail(item['url'])
    except Exception as e:
        logger.warning(f'[SYNC] fetch_detail KO {ad_id} : {e}')
        return 'skipped'

    title       = detail['title'] or item['title']
    description = detail['description'] or ''
    price       = detail['price'] or item['price'] or 0
    location    = detail['location']
    photos_pa   = detail['photos']
    seller_name = detail['seller_name'] or ''
    if detail.get('agency_name'):
        seller_name = (
            f"{seller_name} ({detail['agency_name']})"
            if seller_name else detail['agency_name']
        )

    if existing:
        # Update si modifications
        changed = (
            existing.titre != title or
            existing.description != description or
            existing.prix != price or
            existing.commune != location or
            existing.imported_seller_phone != detail['seller_phone'] or
            existing.imported_seller_email != detail['seller_email']
        )
        if not changed:
            return 'skipped'
        if dry_run:
            return 'updated'

        existing.titre = title
        existing.description = description
        existing.prix = price
        existing.commune = location
        existing.localisation = location
        existing.imported_seller_name  = seller_name
        existing.imported_seller_phone = detail['seller_phone']
        existing.imported_seller_email = detail['seller_email']
        existing.statut = 'actif'
        existing.imported_at = timezone.now()
        existing.save()
        return 'updated'

    # ─── Création ───
    if dry_run:
        return 'created'

    seller_user, was_created = get_or_create_seller_user(
        name=seller_name, phone=detail['seller_phone'], email=detail['seller_email'],
    )
    if was_created:
        stats['users_created'] = stats.get('users_created', 0) + 1

    photo_urls = []
    if not skip_photos and photos_pa:
        for p_url in photos_pa:  # plus de limite
            url_local = _download_and_save_photo(p_url, ad_id)
            if url_local:
                photo_urls.append(url_local)
                stats['photos_downloaded'] += 1

    Annonce.objects.create(
        user=seller_user,
        titre=title,
        description=description,
        prix=price,
        categorie=categorie,
        sous_categorie=sous_cat,
        type_transaction=transaction,
        commune=location,
        localisation=location,
        photos=photo_urls,
        statut='actif',
        is_imported=True,
        external_pa_id=ad_id,
        external_pa_url=item['url'],
        imported_at=timezone.now(),
        imported_seller_name=seller_name,
        imported_seller_phone=detail['seller_phone'],
        imported_seller_email=detail['seller_email'],
    )
    return 'created'


def _download_and_save_photo(url, ad_id):
    """Télécharge une photo PA et la sauvegarde en WebP. Retourne l'URL locale TBG ou None."""
    blob, _ct = pa.download_photo(url)
    if not blob:
        return None
    try:
        file_obj = io.BytesIO(blob)
        file_obj.size = len(blob)
        file_obj.name = urlparse(url).path.split('/')[-1] or 'photo.jpg'
        return save_webp(file_obj, folder='annonces', prefix=f'pa{ad_id}')
    except Exception as e:
        logger.warning(f'[SYNC] save_webp KO pour {url} : {e}')
        return None


def _archive_missing(seen_ad_ids, only_cat):
    """Archive (statut='expire') les annonces is_imported absentes du RSS."""
    if not seen_ad_ids:
        return 0
    qs = Annonce.objects.filter(is_imported=True, statut='actif')
    if only_cat:
        mapping = map_pa_category(only_cat)
        if mapping:
            categorie, sous_cat, transaction = mapping
            qs = qs.filter(categorie=categorie, sous_categorie=sous_cat, type_transaction=transaction)
    qs = qs.exclude(external_pa_id__in=seen_ad_ids)
    count = qs.count()
    if count:
        qs.update(statut='expire')
        logger.info(f'[SYNC] {count} annonces archivées')
    return count
