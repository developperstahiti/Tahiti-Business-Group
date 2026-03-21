"""
Agents automatiques de scraping pour les rubriques TBG.

Scrape des sources polynesiennes, analyse le contenu pour le trier
automatiquement en Promo, Info ou Nouveaute, puis publie.
"""
import logging
import re
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model

logger = logging.getLogger('rubriques.agents')

User = get_user_model()

# ── Sources a scraper (toutes melangees, le tri se fait apres) ────────────────

SOURCES = [
    {
        'name': 'Radio1',
        'url': 'https://www.radio1.pf/',
        'mode': 'heading_links',
        'exclude_patterns': ['/event/', '/category/', '/page/', '/tag/'],
    },
    {
        'name': 'Tahiti Infos',
        'url': 'https://www.tahiti-infos.com/',
        'mode': 'heading_links',
        'exclude_patterns': ['/agenda/', '/annuaire/', '/404'],
    },
    {
        'name': 'Tahiti Infos Eco',
        'url': 'https://www.tahiti-infos.com/Economie_r4.html',
        'mode': 'heading_links',
        'exclude_patterns': ['/404'],
    },
]

MAX_ARTICLES_PER_SOURCE = 5
MAX_TOTAL = 15
REQUEST_TIMEOUT = 15
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (compatible; TBG-Bot/1.0; +https://www.tahitibusinessgroup.com)',
    'Accept-Language': 'fr-FR,fr;q=0.9',
}

# ── Mots-cles pour le tri automatique ─────────────────────────────────────────

PROMO_KEYWORDS = [
    # Prix et reductions
    r'-\d+\s*%', r'\d+\s*%\s*(de\s+)?(reduction|remise|rabais)',
    r'promo', r'promotion', r'solde', r'destockage',
    r'bon\s+plan', r'bons?\s+plans?', r'offre\s+speciale',
    r'prix\s+(casse|choc|bas|reduit|exceptionnel)',
    r'gratuit', r'offert', r'cadeau',
    r'reduction', r'remise', r'rabais', r'ristourne',
    r'moins\s+cher', r'economisez', r'profitez',
    # Commerce
    r'xpf', r'\d[\s\xa0]*\d{3}\s*(f|fcfp|xpf)',
    r'vente\s+flash', r'black\s*friday', r'french\s*days',
    r'liquidation', r'fin\s+de\s+serie',
    r'code\s+promo', r'coupon', r'voucher',
]

NOUVEAUTE_KEYWORDS = [
    # Ouvertures et lancements
    r'ouverture', r'inaugur', r'lance(ment)?',
    r'nouveau(x|te|tes)?', r'nouvelle', r'innov',
    r'ouvre\s+ses?\s+portes?',
    # Entreprises et business
    r'start-?up', r'entreprise\s+(cree|lance|ouvre)',
    r'investiss', r'partenariat', r'franchise',
    r'chiffre\s+d.affaires', r'croissance',
    r'developpement\s+(economique|durable)',
    # Services et infra
    r'fibre\s+optique', r'5g', r'numerique',
    r'application\s+(mobile|web)',
    r'service\s+(public|nouveau|lance)',
    r'transport\s+(aerien|maritime)',
    r'vol\s+(direct|inaugural)', r'liaison\s+(aerienne|maritime)',
    r'hotel|resort|pension|bungalow',
    r'tourisme', r'visiteurs',
    r'restaurant|cafe|brasserie',
]

# Tout ce qui ne matche ni promo ni nouveaute => Info (actualite generale)


def _classify_article(title, content):
    """Classe un article en 'promo', 'nouveaute' ou 'info' selon son contenu."""
    text = f"{title} {content[:1500]}".lower()

    # Compter les matches pour chaque categorie
    promo_score = 0
    for pattern in PROMO_KEYWORDS:
        if re.search(pattern, text, re.IGNORECASE):
            promo_score += 1

    nouveaute_score = 0
    for pattern in NOUVEAUTE_KEYWORDS:
        if re.search(pattern, text, re.IGNORECASE):
            nouveaute_score += 1

    # Seuils : il faut au moins 2 mots-cles pour etre classe
    if promo_score >= 2 and promo_score > nouveaute_score:
        return 'promo'
    if nouveaute_score >= 2 and nouveaute_score > promo_score:
        return 'nouveaute'

    # Par defaut => info (actualite)
    return 'info'


def download_and_save_photo(image_url, prefix='agent'):
    """Telecharge une image distante et la sauvegarde via save_webp (S3 ou local)."""
    if not image_url:
        return ''
    try:
        resp = requests.get(image_url, headers=HEADERS, timeout=10, stream=True)
        resp.raise_for_status()
        content_type = resp.headers.get('Content-Type', '')
        if 'image' not in content_type and not image_url.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif')):
            logger.warning(f"Pas une image: {content_type} | {image_url[:80]}")
            return ''
        from io import BytesIO
        from ads.image_utils import save_webp
        img_data = BytesIO(resp.content)
        img_data.name = 'download.jpg'
        img_data.size = len(resp.content)
        url = save_webp(img_data, 'rubriques', prefix)
        logger.info(f"Photo sauvegardee: {url[:80]}")
        return url
    except Exception as e:
        logger.warning(f"Erreur download photo {image_url[:60]}: {e}")
        return ''


def get_or_create_bot_user():
    """Recupere ou cree le user bot pour les articles automatiques."""
    bot, created = User.objects.get_or_create(
        email='bot@tahitibusinessgroup.com',
        defaults={
            'nom': 'TBG Bot',
            'role': 'admin',
            'is_active': True,
        }
    )
    if created:
        bot.set_unusable_password()
        bot.save()
        logger.info("Bot user cree: bot@tahitibusinessgroup.com")
    return bot


def _fix_encoding(resp):
    """Force UTF-8 si le serveur ne declare pas le bon charset."""
    if resp.encoding and 'utf' not in resp.encoding.lower():
        resp.encoding = 'utf-8'
    if not resp.encoding:
        resp.encoding = 'utf-8'


def scrape_links(source):
    """Scrape les liens d'articles d'une source."""
    try:
        resp = requests.get(source['url'], headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        _fix_encoding(resp)
    except requests.RequestException as e:
        logger.warning(f"[{source['name']}] Erreur HTTP: {e}")
        return []

    soup = BeautifulSoup(resp.text, 'html.parser')
    links = []
    seen_urls = set()
    exclude = source.get('exclude_patterns', [])

    if source.get('mode') == 'heading_links':
        for heading in soup.select('h2, h3, h4'):
            a_tag = heading.find('a')
            if not a_tag:
                a_tag = heading.find_parent('a')
            if not a_tag:
                continue

            href = a_tag.get('href', '')
            if not href or href == '#':
                continue

            href = urljoin(source['url'], href)
            if not href.startswith('http'):
                continue

            if any(pat in href for pat in exclude):
                continue

            title = heading.get_text(strip=True)
            if not title or len(title) < 15:
                continue

            if href not in seen_urls:
                seen_urls.add(href)
                links.append({'url': href, 'title': title, 'source': source['name']})
    else:
        selector = source.get('selector', 'a')
        for a_tag in soup.select(selector)[:20]:
            href = a_tag.get('href', '')
            if not href or href == '#':
                continue
            href = urljoin(source['url'], href)
            if not href.startswith('http'):
                continue
            if any(pat in href for pat in exclude):
                continue

            title = a_tag.get_text(strip=True)
            if not title or len(title) < 15:
                continue

            if href not in seen_urls:
                seen_urls.add(href)
                links.append({'url': href, 'title': title, 'source': source['name']})

    logger.info(f"[{source['name']}] {len(links)} liens trouves")
    return links[:MAX_ARTICLES_PER_SOURCE]


def scrape_article_content(url):
    """Scrape le contenu texte + image d'un article."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        _fix_encoding(resp)
    except requests.RequestException as e:
        logger.warning(f"Erreur scraping {url}: {e}")
        return None, None

    soup = BeautifulSoup(resp.text, 'html.parser')

    # Supprimer les scripts, styles, nav, footer
    for tag in soup.select('script, style, nav, footer, header, aside, .sidebar, .menu, .ad'):
        tag.decompose()

    # Chercher le contenu principal
    content_el = soup.select_one(
        'article, .article-content, .entry-content, .post-content, '
        '.content, main, .main-content, #content'
    )
    if not content_el:
        content_el = soup.body

    # Extraire les paragraphes proprement
    paragraphs = []
    if content_el:
        for p in content_el.select('p'):
            text = p.get_text(strip=True)
            if len(text) > 30:
                paragraphs.append(text)

    # Fallback: texte brut
    if not paragraphs and content_el:
        raw = content_el.get_text(separator='\n', strip=True)
        paragraphs = [line for line in raw.split('\n') if len(line.strip()) > 30]

    content = '\n\n'.join(paragraphs[:15])

    # Trouver une image (og:image en priorite)
    img = None
    og_image = soup.select_one('meta[property="og:image"]')
    if og_image and og_image.get('content'):
        img = og_image['content']
        if not img.startswith('http'):
            img = urljoin(url, img)
    else:
        first_img = (content_el or soup).select_one('img[src]')
        if first_img:
            img_src = first_img.get('src', '')
            if img_src.startswith('http'):
                img = img_src

    return content, img


def _is_duplicate(url):
    """Verifie si l'URL existe deja dans n'importe quelle rubrique."""
    from .models import ArticleInfo, ArticlePromo, ArticleNouveaute
    return (
        ArticleInfo.objects.filter(source_media=url).exists()
        or ArticlePromo.objects.filter(lien_promo=url).exists()
        or ArticleNouveaute.objects.filter(lien_redirection=url).exists()
    )


def run_all_agents(dry_run=False):
    """Scrape toutes les sources, analyse et trie chaque article."""
    from .models import ArticleInfo, ArticlePromo, ArticleNouveaute

    bot = get_or_create_bot_user()
    results = {'info': 0, 'promo': 0, 'nouveaute': 0}
    total = 0

    # 1. Collecter tous les liens de toutes les sources
    all_links = []
    for source in SOURCES:
        links = scrape_links(source)
        all_links.extend(links)

    # Dedupliquer par URL
    seen = set()
    unique_links = []
    for link in all_links:
        if link['url'] not in seen:
            seen.add(link['url'])
            unique_links.append(link)

    logger.info(f"Total: {len(unique_links)} liens uniques")

    # 2. Traiter chaque article
    for link in unique_links:
        if total >= MAX_TOTAL:
            break

        # Anti-doublon global (cherche dans les 3 tables)
        if _is_duplicate(link['url']):
            continue

        if dry_run:
            logger.info(f"[DRY RUN] {link['title'][:60]} | {link['url'][:60]}")
            total += 1
            continue

        # Scraper le contenu complet
        content, photo_url = scrape_article_content(link['url'])
        if not content or len(content) < 100:
            continue

        # Classifier l'article
        category = _classify_article(link['title'], content)

        # Telecharger la photo
        saved_photo = download_and_save_photo(photo_url, f'{category}_{results[category]}')

        # Publier dans la bonne rubrique
        if category == 'promo':
            ArticlePromo.objects.create(
                pro_user=bot,
                titre=link['title'][:200],
                contenu=content,
                photo=saved_photo,
                lien_promo=link['url'],
                statut='valide',
            )
        elif category == 'nouveaute':
            ArticleNouveaute.objects.create(
                pro_user=bot,
                titre=link['title'][:200],
                contenu=content,
                photo=saved_photo,
                lien_redirection=link['url'],
                statut='valide',
            )
        else:  # info
            ArticleInfo.objects.create(
                auteur=bot,
                titre=link['title'][:200],
                contenu=content,
                photo=saved_photo,
                source_media=link['url'],
                statut='valide',
            )

        results[category] += 1
        total += 1
        logger.info(f"[{category.upper()}] {link['title'][:60]}")

    logger.info(f"Termine: {results} (total={total})")
    return results
