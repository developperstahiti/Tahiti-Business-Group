"""
Management command : python manage.py import_ads
Importe jusqu'à 50 annonces depuis petites-annonces.pf vers TBG.
Relançable sans créer de doublons (vérification via source_url dans specs).
"""
import io
import os
import re
import time
import uuid

import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from PIL import Image as PILImage

from ads.models import Annonce

User = get_user_model()

BASE_URL   = 'https://www.petites-annonces.pf'
HEADERS    = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    )
}
DELAY      = 2        # secondes entre requêtes
MAX_IMPORT = 50       # par lancement
MAX_PHOTOS = 4        # photos max par annonce

# Catégories cibles : c= -> catégorie TBG
# (on ignore les catégories non pertinentes)
CATEGORY_MAP = {
    # Immobilier
    '1': 'immobilier', '2': 'immobilier', '3': 'immobilier',
    '4': 'immobilier', '5': 'immobilier', '6': 'immobilier',
    '7': 'immobilier',
    # Véhicules
    '9': 'vehicules', '10': 'vehicules', '11': 'vehicules',
    '12': 'vehicules', '13': 'vehicules',
    '58': 'vehicules', '59': 'vehicules', '60': 'vehicules',
    # Électronique / Bonnes affaires
    '15': 'autres',      '16': 'autres',
    '17': 'electronique', '18': 'electronique',
    '19': 'electronique', '20': 'electronique',
    '21': 'autres',      '22': 'autres',      '23': 'autres',
    '24': 'autres',      '25': 'autres',      '26': 'autres',
    '51': 'autres',      '52': 'autres',      '53': 'autres',
    '54': 'autres',
    # Emploi
    '28': 'emploi', '29': 'emploi', '30': 'emploi', '31': 'emploi',
    # Services
    '32': 'services', '34': 'services', '36': 'services',
    '37': 'services', '38': 'services', '39': 'services',
}

# Catégories à scraper en priorité (les plus actives)
TARGET_CATS = [
    ('9',  'vehicules'),    # Vends voiture
    ('10', 'vehicules'),    # Vends 2 roues
    ('11', 'vehicules'),    # Vends bateau
    ('1',  'immobilier'),   # Vends appartement
    ('2',  'immobilier'),   # Vends maison
    ('17', 'electronique'), # Informatique
    ('19', 'electronique'), # TV, Hi-fi
    ('20', 'electronique'), # Téléphonie
    ('28', 'emploi'),       # Offres emploi
    ('36', 'services'),     # Prestataires divers
    ('15', 'autres'),       # Meubles & Electroménager
]

IMPORT_USER_EMAIL = 'import@tbg.pf'


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get(url, **kwargs):
    """GET avec délai et headers."""
    time.sleep(DELAY)
    try:
        r = requests.get(url, headers=HEADERS, timeout=15, **kwargs)
        r.raise_for_status()
        return r
    except Exception:
        return None


def _parse_prix(text):
    """Extrait un prix entier depuis un texte comme 'PRIX : 1 900 000 XPF'."""
    m = re.search(r'([\d\s]+)\s*(?:XPF|FCFP|F CFP)', text, re.I)
    if m:
        digits = re.sub(r'\s', '', m.group(1))
        try:
            return int(digits)
        except ValueError:
            pass
    return 0


def _parse_prix_label(text):
    """Retourne le label brut du prix ('1 900 000 XPF')."""
    m = re.search(r'PRIX\s*:\s*([\d\s]+(?:XPF|FCFP|F CFP)[^\n<]*)', text, re.I)
    if m:
        return m.group(1).strip()[:50]
    return ''


def _download_image(img_url, user_pk):
    """Télécharge une image et la sauvegarde en WebP. Retourne l'URL/path relative."""
    r = _get(img_url)
    if not r or not r.content:
        return None
    try:
        img = PILImage.open(io.BytesIO(r.content)).convert('RGB')
        img.thumbnail((900, 700), PILImage.LANCZOS)

        # S3 si disponible
        if os.environ.get('AWS_STORAGE_BUCKET_NAME'):
            import boto3
            bucket = os.environ['AWS_STORAGE_BUCKET_NAME']
            region = os.environ.get('AWS_S3_REGION_NAME', 'eu-north-1')
            key = f"annonces/{user_pk}_{uuid.uuid4().hex[:8]}.webp"
            buf = io.BytesIO()
            img.save(buf, format='WEBP', quality=82, method=6)
            buf.seek(0)
            boto3.client(
                's3', region_name=region,
                aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
            ).put_object(Bucket=bucket, Key=key, Body=buf, ContentType='image/webp')
            return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"

        # Local
        save_dir = os.path.join(settings.MEDIA_ROOT, 'annonces')
        os.makedirs(save_dir, exist_ok=True)
        filename = f"{user_pk}_{uuid.uuid4().hex[:8]}.webp"
        img.save(os.path.join(save_dir, filename), format='WEBP', quality=82, method=6)
        return f"{settings.MEDIA_URL}annonces/{filename}"
    except Exception:
        return None


def _get_ad_links(cat_code, page=1):
    """Retourne les (href, photo_thumb) des annonces sur une page de liste."""
    url = f"{BASE_URL}/annonces.php?c={cat_code}&p={page}"
    r = _get(url)
    if not r:
        return []
    soup = BeautifulSoup(r.text, 'html.parser')
    results = []
    for a in soup.select('a.lda'):
        href = a.get('href', '')
        if not href or 'tahiti=' not in href:
            continue
        img_tag = a.select_one('img.ph')
        thumb = img_tag.get('src', '') if img_tag else ''
        results.append((href, thumb))
    return results


def _scrape_detail(href):
    """
    Scrape une page de détail.
    Retourne un dict ou None si annonce invalide.
    """
    url = f"{BASE_URL}/{href}"
    r = _get(url)
    if not r:
        return None

    soup = BeautifulSoup(r.text, 'html.parser')
    text = r.text

    # ── Titre ──────────────────────────────────────────────────────────────
    h3s = soup.select('h3')
    titre = ''
    for h in h3s:
        t = h.get_text(strip=True)
        if t and t not in ('DESCRIPTIF', 'CONTACTS & INFOS', 'CONTACTER LE VENDEUR PAR EMAIL'):
            titre = t
            break
    if not titre:
        return None

    # ── Description ────────────────────────────────────────────────────────
    desc = ''
    # find() avec string= ne matche pas si le h3 a des sous-éléments
    desc_h3 = None
    for h in soup.find_all('h3'):
        if 'DESCRIPTIF' in h.get_text(strip=True).upper():
            desc_h3 = h
            break
    if desc_h3:
        el = desc_h3.find_next_sibling()
        while el:
            t = el.get_text(separator='\n', strip=True)
            if t and el.name not in ('h3', 'form'):
                desc = t
                break
            if el.name == 'h3':
                break
            el = el.find_next_sibling()
    # Fallback : chercher le texte entre DESCRIPTIF et CONTACTS
    if not desc:
        full_text = soup.get_text(separator='\n')
        m = re.search(r'DESCRIPTIF\s*\n(.*?)\n(?:CONTACTS|CONTACTER)', full_text, re.S | re.I)
        if m:
            desc = m.group(1).strip()
    if not desc:
        return None

    # ── Prix ───────────────────────────────────────────────────────────────
    prix = 0
    prix_label = ''
    for p in soup.select('p'):
        txt = p.get_text(strip=True)
        if 'PRIX' in txt.upper():
            prix = _parse_prix(txt)
            prix_label = _parse_prix_label(txt)
            break

    # ── Localisation ───────────────────────────────────────────────────────
    localisation = 'Tahiti'
    loc_m = re.search(
        r'(?:Localisation|Commune|Lieu|Ville)\s*[:\-]\s*([A-Za-zÀ-ÿ\s\-]+)',
        text, re.I
    )
    if loc_m:
        localisation = loc_m.group(1).strip()[:100]

    # ── Photos (versions grand format photo/bIDNUM.jpg) ───────────────────
    photo_urls = []
    for img in soup.select('img'):
        src = img.get('src', '')
        if re.match(r'photo/b?\d+\.jpg', src):
            # Préférer la version grande (b prefix)
            big = re.sub(r'photo/(\d+)', r'photo/b\1', src)
            photo_urls.append(f"{BASE_URL}/{big}")
    # Dédoublonner
    seen = set()
    unique_photos = []
    for u in photo_urls:
        if u not in seen:
            seen.add(u)
            unique_photos.append(u)

    if not unique_photos:
        return None  # Ignorer les annonces sans photo

    return {
        'source_url': url,
        'titre': titre[:200],
        'description': desc,
        'prix': prix,
        'prix_label': prix_label,
        'localisation': localisation,
        'photo_urls': unique_photos[:MAX_PHOTOS],
    }


# ─── Command ──────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = 'Importe jusqu\'à 50 annonces depuis petites-annonces.pf (sans doublons)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--max', type=int, default=MAX_IMPORT,
            help='Nombre max d\'annonces à importer (défaut: 50)'
        )
        parser.add_argument(
            '--cat', type=str, default='',
            help='Forcer une catégorie spécifique (ex: vehicules)'
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Scraper sans rien enregistrer en base'
        )

    def handle(self, *args, **options):
        max_import = options['max']
        force_cat  = options['cat']
        dry_run    = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('[DRY RUN] Aucune donnée ne sera sauvegardée.\n'))

        # ── Utilisateur import ─────────────────────────────────────────────
        import_user, created = User.objects.get_or_create(
            email=IMPORT_USER_EMAIL,
            defaults={
                'nom': 'Import TBG',
                'role': 'pro',
                'is_active': True,
            }
        )
        if created:
            import_user.set_password(uuid.uuid4().hex)
            import_user.save()
            self.stdout.write(f'  Utilisateur import créé : {IMPORT_USER_EMAIL}')

        # ── Scraping ───────────────────────────────────────────────────────
        imported = 0
        skipped_dup = 0
        skipped_err = 0

        for cat_code, tbg_cat in TARGET_CATS:
            if force_cat and tbg_cat != force_cat:
                continue
            if imported >= max_import:
                break

            self.stdout.write(f'\n-> Catégorie c={cat_code} ({tbg_cat})')

            for page in range(1, 6):  # max 5 pages par catégorie
                if imported >= max_import:
                    break

                ad_links = _get_ad_links(cat_code, page)
                if not ad_links:
                    break

                self.stdout.write(f'  Page {page} : {len(ad_links)} annonces trouvées')

                for href, _thumb in ad_links:
                    if imported >= max_import:
                        break

                    source_url = f"{BASE_URL}/{href}"

                    # ── Vérification doublon ───────────────────────────────
                    if Annonce.objects.filter(specs__source_url=source_url).exists():
                        skipped_dup += 1
                        continue

                    # ── Scraping de la page détail ─────────────────────────
                    data = _scrape_detail(href)
                    if not data:
                        skipped_err += 1
                        continue

                    mention = (
                        f"\n\n---\n"
                        f"[Import] Annonce importée depuis petites-annonces.pf pour donner plus "
                        f"de visibilité au vendeur.\n"
                        f"Voir l'annonce originale : {source_url}"
                    )
                    description_complete = data['description'] + mention

                    if dry_run:
                        self.stdout.write(
                            f"  [DRY] {data['titre'][:60]} | {data['prix_label'] or data['prix']} | "
                            f"{len(data['photo_urls'])} photo(s)"
                        )
                        imported += 1
                        continue

                    # ── Téléchargement des photos ──────────────────────────
                    photos_saved = []
                    for img_url in data['photo_urls']:
                        saved = _download_image(img_url, import_user.pk)
                        if saved:
                            photos_saved.append(saved)

                    if not photos_saved:
                        skipped_err += 1
                        continue

                    # ── Création de l'annonce ──────────────────────────────
                    Annonce.objects.create(
                        user=import_user,
                        titre=data['titre'],
                        description=description_complete,
                        prix=data['prix'],
                        prix_label=data['prix_label'],
                        categorie=tbg_cat,
                        localisation=data['localisation'],
                        photos=photos_saved,
                        statut='actif',
                        specs={
                            'source_url':  source_url,
                            'source_site': 'petites-annonces.pf',
                        },
                    )
                    imported += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  [OK] [{imported}/{max_import}] {data['titre'][:55]}"
                        )
                    )

        # ── Résumé ─────────────────────────────────────────────────────────
        self.stdout.write('\n' + '-' * 50)
        self.stdout.write(self.style.SUCCESS(f'Importées  : {imported}'))
        self.stdout.write(f'Doublons ignorés  : {skipped_dup}')
        self.stdout.write(f'Erreurs/sans photo: {skipped_err}')
        self.stdout.write(
            '\n  Pour relancer : python manage.py import_ads\n'
            '  Dry run       : python manage.py import_ads --dry-run\n'
            '  Par catégorie : python manage.py import_ads --cat vehicules\n'
        )
