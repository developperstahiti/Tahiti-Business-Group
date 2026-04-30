"""Moteur de synchronisation petites-annonces.pf → TBG.

Stratégie :
- Pour chaque catégorie PA (c=1..6 pour immobilier) :
  - Fetch RSS → liste d'annonces
  - Pour chaque annonce :
    - Si already imported (external_pa_id) : update si nécessaire
    - Sinon : fetch_detail + create
  - Track des ad_id vus dans cette session
- À la fin : archive les annonces is_imported dont l'ad_id n'a pas été vu
  (statut='expire')

Usage :
    from ads.scrapers.sync import sync_immobilier
    stats = sync_immobilier(limit=50, dry_run=True)
"""
import io
import logging
from datetime import datetime
from urllib.parse import urlparse

from django.contrib.auth import get_user_model
from django.utils import timezone

from ads.models import Annonce, PASyncRun
from ads.image_utils import save_webp
from ads.scrapers import petitesannonces_pf as pa
from ads.scrapers.category_mapper import IMMOBILIER_CATEGORIES, map_pa_category

logger = logging.getLogger(__name__)
User = get_user_model()

SYSTEM_USER_EMAIL = 'petitesannonces@tbg.local'
SYSTEM_USER_NAME  = 'Petites Annonces PF'


def get_system_user():
    """Crée (ou récupère) le user système qui possède toutes les annonces importées."""
    user, created = User.objects.get_or_create(
        email=SYSTEM_USER_EMAIL,
        defaults={
            'nom':       SYSTEM_USER_NAME,
            'is_active': True,
        },
    )
    if created:
        user.set_unusable_password()
        user.save(update_fields=['password'])
        logger.info(f'[SYNC] User système créé : {SYSTEM_USER_EMAIL}')
    return user


def sync_immobilier(limit=None, dry_run=False, skip_photos=False, only_cat=None,
                    triggered_by=None):
    """Synchronise toutes les sous-catégories immobilier de PA.

    Args:
        limit        : max d'annonces à traiter par catégorie (None = toutes)
        dry_run      : si True, ne crée/modifie rien en DB
        skip_photos  : si True, ne télécharge pas les photos
        only_cat     : si fourni (int), traite uniquement cette catégorie PA
        triggered_by : User qui a lancé (None = cron)

    Retourne un dict de stats : created, updated, archived, errors, skipped
    """
    stats = {
        'created':  0,
        'updated':  0,
        'archived': 0,
        'errors':   0,
        'skipped':  0,
        'photos_downloaded': 0,
    }
    error_messages = []  # capture les détails d'erreurs pour debug
    seen_ad_ids = set()

    cats_to_process = [only_cat] if only_cat else IMMOBILIER_CATEGORIES

    # Crée un SyncRun pour tracking (sauf en dry-run)
    run = None
    if not dry_run:
        run = PASyncRun.objects.create(triggered_by=triggered_by, status='running')

    system_user = get_system_user() if not dry_run else None

    for c_id in cats_to_process:
        mapping = map_pa_category(c_id)
        if not mapping:
            logger.warning(f'[SYNC] Catégorie PA c={c_id} non mappée, skip')
            continue
        categorie, sous_cat, transaction = mapping

        try:
            items = pa.fetch_rss(c_id)
        except Exception as e:
            err = f'fetch_rss c={c_id} : {type(e).__name__}: {e}'
            logger.error(f'[SYNC] {err}')
            error_messages.append(err)
            stats['errors'] += 1
            continue

        if limit:
            items = items[:limit]

        for idx, item in enumerate(items):
            ad_id = item['ad_id']
            seen_ad_ids.add(ad_id)
            try:
                result = _process_item(
                    item, categorie, sous_cat, transaction,
                    system_user=system_user,
                    dry_run=dry_run, skip_photos=skip_photos,
                )
                stats[result] = stats.get(result, 0) + 1
                if result == 'created' and not skip_photos:
                    stats['photos_downloaded'] += _last_photo_count
            except Exception as e:
                err = f'process ad_id={ad_id} : {type(e).__name__}: {e}'
                logger.exception(f'[SYNC] {err}')
                error_messages.append(err)
                stats['errors'] += 1
            finally:
                pa.polite_sleep()

        logger.info(
            f'[SYNC] c={c_id} terminé. Créés={stats["created"]} '
            f'Maj={stats["updated"]} Skip={stats["skipped"]}'
        )

    # Phase d'archivage : annonces is_imported absentes du RSS courant
    if not dry_run:
        archived = _archive_missing(seen_ad_ids, only_cat)
        stats['archived'] = archived

    # Finalise le SyncRun
    if run:
        run.finished_at = timezone.now()
        run.status = 'success' if stats['errors'] == 0 else 'error'
        run.nb_created  = stats['created']
        run.nb_updated  = stats['updated']
        run.nb_archived = stats['archived']
        run.nb_skipped  = stats['skipped']
        run.nb_errors   = stats['errors']
        run.nb_photos   = stats['photos_downloaded']
        run.error_msg   = '\n'.join(error_messages[:20])  # max 20 erreurs détaillées
        run.save()

    return stats


_last_photo_count = 0


def _process_item(item, categorie, sous_cat, transaction, *,
                  system_user, dry_run, skip_photos):
    """Traite une annonce du RSS.

    Retourne 'created', 'updated' ou 'skipped'.
    """
    global _last_photo_count
    _last_photo_count = 0

    ad_id = item['ad_id']
    existing = Annonce.objects.filter(external_pa_id=ad_id).first()

    # Fetch les détails (toujours nécessaire pour photos+contact)
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
        seller_name = f"{seller_name} ({detail['agency_name']})" if seller_name else detail['agency_name']

    if existing:
        # ─── Update si modifications détectées ───
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
            logger.info(f'[DRY] Update {ad_id}: {title[:60]}')
            return 'updated'

        existing.titre = title
        existing.description = description
        existing.prix = price
        existing.commune = location
        existing.localisation = location
        existing.imported_seller_name  = seller_name
        existing.imported_seller_phone = detail['seller_phone']
        existing.imported_seller_email = detail['seller_email']
        existing.statut = 'actif'  # Réactive si elle avait été archivée
        existing.imported_at = timezone.now()
        existing.save()
        logger.info(f'[SYNC] Update {ad_id}: {title[:60]}')
        return 'updated'

    # ─── Création ───
    if dry_run:
        logger.info(f'[DRY] Create {ad_id}: {title[:60]} | {price:,} XPF')
        return 'created'

    photo_urls = []
    if not skip_photos and photos_pa:
        for p_url in photos_pa[:5]:  # max 5 photos
            url_local = _download_and_save_photo(p_url, ad_id)
            if url_local:
                photo_urls.append(url_local)
                _last_photo_count += 1

    annonce = Annonce.objects.create(
        user=system_user,
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
    logger.info(f'[SYNC] Create {ad_id} → annonce TBG #{annonce.pk}: {title[:60]}')
    return 'created'


def _download_and_save_photo(url, ad_id):
    """Télécharge une photo PA et la sauvegarde en WebP via save_webp().

    Retourne l'URL locale TBG ou None en cas d'échec.
    """
    blob, ct = pa.download_photo(url)
    if not blob:
        return None
    try:
        # save_webp attend un fichier-like avec .read() et optionnellement .size
        file_obj = io.BytesIO(blob)
        file_obj.size = len(blob)
        file_obj.name = urlparse(url).path.split('/')[-1] or 'photo.jpg'
        url_local = save_webp(file_obj, folder='annonces', prefix=f'pa{ad_id}')
        return url_local
    except Exception as e:
        logger.warning(f'[SYNC] save_webp KO pour {url} : {e}')
        return None


def _archive_missing(seen_ad_ids, only_cat):
    """Archive (statut='expire') les annonces is_imported dont l'ad_id n'est plus dans le RSS.

    Si only_cat est fourni, restreint l'archivage aux annonces de cette catégorie.
    """
    if not seen_ad_ids:
        return 0  # Sécurité : si fetch a tout raté, ne rien archiver

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
        logger.info(f'[SYNC] {count} annonces archivées (absentes du RSS)')
    return count
