"""Scraper pour petites-annonces.pf (RSS + page détail).

Stratégie :
1. RSS par catégorie (rapide, propre) → liste d'annonces avec id + url + titre + prix
2. Pour chaque annonce nouvelle : fetch HTML détail → photos, contact, description complète
3. Téléchargement des photos en local

Note : PA ne donne pas de classes CSS propres → parsing positionnel + regex.
"""
import logging
import re
import time
from urllib.parse import urlparse, parse_qs, urljoin

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = 'https://www.petites-annonces.pf'
RSS_URL  = f'{BASE_URL}/rss.php'
USER_AGENT = 'TBG-Sync/1.0 (+https://tahitibusinessgroup.com)'

DEFAULT_TIMEOUT = 15
DEFAULT_DELAY   = 0.5  # délai entre 2 requêtes pour ne pas saturer PA


def _http_get(url, timeout=DEFAULT_TIMEOUT):
    """GET avec User-Agent et timeout."""
    return requests.get(
        url,
        headers={'User-Agent': USER_AGENT},
        timeout=timeout,
    )


# ──────────────────────────────────────────────────────────────────
#  RSS
# ──────────────────────────────────────────────────────────────────
def fetch_rss(c_id):
    """Récupère le flux RSS d'une catégorie.

    Retourne une liste de dicts : {ad_id, url, title, category, description_html, price}

    Note : PA déclare encoding=utf8 mais le contenu est en iso-8859-1.
    On décode manuellement et on parse avec BeautifulSoup (xml mode).
    """
    url = f'{RSS_URL}?c={c_id}'
    logger.info(f'[PA] Fetch RSS {url}')
    resp = _http_get(url)
    resp.raise_for_status()

    # Force iso-8859-1 (encoding réel du flux PA)
    try:
        text = resp.content.decode('iso-8859-1')
    except UnicodeDecodeError:
        text = resp.content.decode('utf-8', errors='replace')
    # Retire la déclaration XML pour éviter les conflits d'encoding
    text = re.sub(r'<\?xml[^>]*\?>', '', text, count=1)

    soup = BeautifulSoup(text, 'xml')
    items = []
    for item in soup.find_all('item'):
        title_el = item.find('title')
        link_el  = item.find('link')
        desc_el  = item.find('description')
        cat_el   = item.find('category')

        title = (title_el.get_text(strip=True) if title_el else '').strip()
        link  = (link_el.get_text(strip=True) if link_el else '').strip()
        desc  = desc_el.get_text() if desc_el else ''
        cat_text = (cat_el.get_text(strip=True) if cat_el else '').strip()

        ad_id = _extract_ad_id(link)
        if not ad_id:
            continue

        items.append({
            'ad_id':            ad_id,
            'url':              link,
            'title':            title,
            'category':         cat_text,
            'description_html': desc,
            'price':            _extract_price(desc),
        })
    logger.info(f'[PA] RSS c={c_id} → {len(items)} items')
    return items


def _extract_ad_id(url):
    """Extrait l'id depuis ?tahiti=NNNNN."""
    if not url:
        return None
    qs = parse_qs(urlparse(url).query)
    val = qs.get('tahiti', [None])[0]
    return val


_PRICE_RE = re.compile(r'(?:Prix\s*:\s*)?([\d\s \.\,]{2,})\s*XPF', re.IGNORECASE)

def _extract_price(text):
    """Extrait le prix XPF depuis la description CDATA."""
    if not text:
        return 0
    # Garde uniquement le HTML stripped pour matcher
    soup = BeautifulSoup(text, 'html.parser')
    plain = soup.get_text(' ', strip=True)
    m = _PRICE_RE.search(plain)
    if not m:
        return 0
    raw = m.group(1)
    digits = re.sub(r'[^\d]', '', raw)
    try:
        return int(digits)
    except (ValueError, TypeError):
        return 0


# ──────────────────────────────────────────────────────────────────
#  Page détail
# ──────────────────────────────────────────────────────────────────
def fetch_detail(url):
    """Récupère et parse une page détail d'annonce PA.

    Retourne un dict :
      title, description, location, photos (URLs absolues),
      seller_name, seller_phone, seller_email, agency_name,
      ad_id, is_pro, price (peut compléter celui du RSS)
    """
    logger.info(f'[PA] Fetch detail {url}')
    resp = _http_get(url)
    resp.raise_for_status()
    # PA déclare utf-8 mais sert iso-8859-1
    try:
        html = resp.content.decode('iso-8859-1')
    except UnicodeDecodeError:
        html = resp.content.decode('utf-8', errors='replace')
    soup = BeautifulSoup(html, 'html.parser')

    sections = _index_sections(soup)
    plain_text = soup.get_text('\n', strip=True)

    contacts_text = _section_text(soup, sections, 'CONTACTS')

    return {
        'ad_id':        _extract_ad_id(url),
        'title':        _parse_title(sections),
        'description':  _section_text(soup, sections, 'DESCRIPTIF'),
        'location':     _parse_location_from_title(_parse_title(sections)),
        'photos':       _parse_photos(soup),
        'seller_name':  _parse_seller_name_from_contacts(contacts_text),
        'seller_phone': _parse_seller_phone(contacts_text or plain_text),
        'seller_email': _parse_seller_email(contacts_text or plain_text),
        'agency_name':  _parse_agency_name(sections),
        'is_pro':       _is_pro(sections),
        'price':        _extract_price(plain_text),
    }


def _index_sections(soup):
    """Indexe les h2/h3 par contenu pour faciliter le découpage.

    Retourne une liste ordonnée de tuples (tag, text, element).
    """
    return [(t.name, t.get_text(strip=True), t) for t in soup.find_all(['h2', 'h3'])]


def _section_text(soup, sections, keyword):
    """Renvoie le texte qui suit la section dont le titre contient `keyword`,
    jusqu'à la section suivante.
    """
    keyword_upper = keyword.upper()
    for i, (tag, text, el) in enumerate(sections):
        if keyword_upper in text.upper():
            next_el = sections[i+1][2] if i+1 < len(sections) else None
            parts = []
            for sib in el.next_siblings:
                if sib == next_el:
                    break
                if hasattr(sib, 'get_text'):
                    parts.append(sib.get_text(' ', strip=True))
                elif isinstance(sib, str):
                    parts.append(sib.strip())
            return ' '.join(p for p in parts if p).strip()
    return ''


def _parse_title(sections):
    """Le titre de l'annonce = h3 qui suit 'DETAILS DE L'ANNONCE'
    (ou avant DESCRIPTIF), en sautant 'Enseigne : ...'.
    """
    skip = ('RUBRIQUES', 'ENSEIGNE', 'DESCRIPTIF', 'CONTACTS', 'CONTACTER',
            'TOP AFFAIRE', 'POSTER', 'INSCRIPTION', 'BOOSTER', 'COMMENT')
    seen_details = False
    for tag, text, _el in sections:
        upper = text.upper()
        if 'DETAILS DE L' in upper or 'DÉTAILS DE L' in upper:
            seen_details = True
            continue
        if not seen_details:
            continue
        if any(s in upper for s in skip):
            continue
        if 2 < len(text) < 200:
            return text
    # Fallback : 1er h3 non-bruit
    for tag, text, _el in sections:
        if tag == 'h3' and not any(s in text.upper() for s in skip):
            if 2 < len(text) < 200:
                return text
    return ''


def _parse_agency_name(sections):
    """Pour les PROs, l'enseigne est dans 'Enseigne :NEXTIMMO'."""
    for _tag, text, _el in sections:
        if 'ENSEIGNE' in text.upper():
            # 'Enseigne :NEXTIMMO' → 'NEXTIMMO'
            parts = re.split(r'[:\s]+', text, maxsplit=1)
            if len(parts) > 1:
                return parts[1].strip()
    return ''


def _is_pro(sections):
    for _tag, text, _el in sections:
        if '(PRO)' in text:
            return True
    return False


def _parse_seller_name_from_contacts(contacts_text):
    """Le bloc CONTACTS est typiquement : 'Sabrina au 89 79 89 18 // sabrina@nextimmo.pf'
    Le nom est avant ' au ' (téléphone) ou avant ' // ' (email).
    """
    if not contacts_text:
        return ''
    # Cherche pattern 'NOM au TELEPHONE' ou 'NOM // EMAIL'
    m = re.match(r'^([^/0-9]+?)\s+au\s+', contacts_text)
    if m:
        return m.group(1).strip()
    m = re.match(r'^([^/0-9]+?)\s*//', contacts_text)
    if m:
        return m.group(1).strip()
    # Fallback : 1ers mots qui ne contiennent pas de chiffres ni @
    first_part = re.split(r'[/\d@]', contacts_text, maxsplit=1)[0].strip()
    return first_part if 2 < len(first_part) < 60 else ''


_PHONE_RE = re.compile(r'(?:(?:\+?689\s*)?(?:\d{2}[\s\.\-]?){3,4}\d{2})')

def _parse_seller_phone(plain):
    """Extrait un numéro polynésien (8 ou 9 chiffres formatés)."""
    matches = _PHONE_RE.findall(plain)
    for m in matches:
        digits = re.sub(r'\D', '', m)
        if 8 <= len(digits) <= 11:
            return m.strip()
    return ''


_EMAIL_RE = re.compile(r'[\w\.\-+]+@[\w\.\-]+\.\w{2,}')

def _parse_seller_email(plain):
    m = _EMAIL_RE.search(plain)
    return m.group(0) if m else ''


def _parse_location_from_title(title):
    """Cherche un nom de commune polynésienne dans le titre."""
    if not title:
        return ''
    COMMUNES = [
        'PAPEETE', 'FAAA', 'PUNAAUIA', 'PAEA', 'PAPARA', 'MAHINA', 'ARUE',
        'PIRAE', 'TARAVAO', 'TAIARAPU', 'HITIAA', 'PAPENOO', 'TEVA I UTA',
        'MOOREA', 'BORA BORA', 'BORA-BORA', 'RAIATEA', 'TAHAA', 'TAHA\'A',
        'HUAHINE', 'MAUPITI', 'TUBUAI', 'RURUTU', 'RAPA', 'HIVA OA',
        'HIVA-OA', 'NUKU HIVA', 'NUKU-HIVA', 'UA POU', 'UA-POU',
        'RANGIROA', 'FAKARAVA', 'TIKEHAU', 'MANIHI', 'MAKEMO', 'TAHITI',
    ]
    upper = title.upper()
    for c in COMMUNES:
        if c in upper:
            # Renvoie la version capitalisée
            return c.title().replace('-', ' ')
    return ''


_PHOTO_RE = re.compile(r'photo/b\d+\.(jpg|jpeg|png|webp)', re.IGNORECASE)

def _parse_photos(soup):
    """Trouve les URL des photos de l'annonce.

    PA stocke les photos d'annonces sous photo/bNNNNNN.jpg (préfixe 'b' = big).
    Les photos sans préfixe 'b' sont les thumbnails de la sidebar (autres annonces).
    """
    urls = []
    seen = set()
    for img in soup.find_all('img'):
        src = img.get('src', '')
        if not src or src in seen:
            continue
        if _PHOTO_RE.search(src):
            full_url = urljoin(BASE_URL + '/', src)
            urls.append(full_url)
            seen.add(src)
    return urls


# ──────────────────────────────────────────────────────────────────
#  Photos — téléchargement
# ──────────────────────────────────────────────────────────────────
def download_photo(url, max_size_mb=10):
    """Télécharge une photo et retourne (bytes, content_type) ou (None, None) si erreur."""
    try:
        resp = _http_get(url, timeout=20)
        resp.raise_for_status()
        ct = resp.headers.get('Content-Type', '').lower()
        if not ct.startswith('image/'):
            logger.warning(f'[PA] {url} : Content-Type non-image ({ct})')
            return None, None
        if len(resp.content) > max_size_mb * 1024 * 1024:
            logger.warning(f'[PA] {url} : photo trop lourde ({len(resp.content)} octets)')
            return None, None
        return resp.content, ct
    except requests.RequestException as e:
        logger.error(f'[PA] download error {url} : {e}')
        return None, None


def polite_sleep(seconds=DEFAULT_DELAY):
    """Petite pause entre 2 requêtes pour ne pas saturer PA."""
    time.sleep(seconds)
