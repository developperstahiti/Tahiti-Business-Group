"""
Agents automatiques de scraping pour les rubriques TBG.

Scrape TOUTES les sources polynesiennes (avec pagination pour remonter
jusqu'a 2 mois), analyse le contenu pour le trier automatiquement
en Promo, Info ou Nouveaute, puis publie.
"""
import logging
import re
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model

logger = logging.getLogger('rubriques.agents')

User = get_user_model()

# ── TOUTES les sources polynesiennes avec pagination ──────────────────────────
# Chaque source a une liste de pages a scraper pour couvrir ~2 mois d'articles

def _build_sources():
    """Genere la liste complete des sources avec pages paginatees."""
    sources = []

    # ── Radio1 (WordPress, ~16 articles/page) ──
    # 10 pages x 16 = ~160 articles (~2 mois)
    for page in range(1, 11):
        if page == 1:
            url = 'https://www.radio1.pf/category/actus/'
        else:
            url = f'https://www.radio1.pf/category/actus/page/{page}/'
        sources.append({
            'name': f'Radio1 p{page}',
            'url': url,
            'mode': 'heading_links',
            'exclude_patterns': ['/event/', '/category/', '/page/', '/tag/'],
        })

    # ── Tahiti Infos (accueil + pages, ~40 articles/page) ──
    # 5 pages x 40 = ~200 articles (~2 mois)
    for page in range(1, 6):
        if page == 1:
            url = 'https://www.tahiti-infos.com/'
        else:
            url = f'https://www.tahiti-infos.com/?page={page}'
        sources.append({
            'name': f'Tahiti Infos p{page}',
            'url': url,
            'mode': 'heading_links',
            'exclude_patterns': ['/agenda/', '/annuaire/', '/404'],
        })

    # ── Tahiti Infos Economie (force en promo) ──
    sources.append({
        'name': 'Tahiti Infos Eco',
        'url': 'https://www.tahiti-infos.com/Economie_r4.html',
        'mode': 'heading_links',
        'exclude_patterns': ['/404'],
        'force_category': 'promo',
    })

    # ── Outremers360 Economie (force en promo) ──
    for page in range(1, 4):
        if page == 1:
            url = 'https://outremers360.com/economie'
        else:
            url = f'https://outremers360.com/economie/page/{page}'
        sources.append({
            'name': f'Outremers360 Eco p{page}',
            'url': url,
            'mode': 'heading_links',
            'exclude_patterns': ['/category/', '/tag/', '/page/', '/author/'],
            'force_category': 'promo',
        })

    # ── Tahiti News (WordPress, ~15 articles/page) ──
    # 8 pages x 15 = ~120 articles (~2 mois)
    for page in range(1, 9):
        if page == 1:
            url = 'https://tahitinews.co/'
        else:
            url = f'https://tahitinews.co/page/{page}/'
        sources.append({
            'name': f'TahitiNews p{page}',
            'url': url,
            'mode': 'heading_links',
            'exclude_patterns': ['/category/', '/tag/', '/page/'],
        })

    # ── Outremers360 Pacifique (~20 articles/page) ──
    # 5 pages x 20 = ~100 articles (~2 mois Pacifique)
    for page in range(1, 6):
        if page == 1:
            url = 'https://outremers360.com/bassin-pacifique'
        else:
            url = f'https://outremers360.com/bassin-pacifique/page/{page}'
        sources.append({
            'name': f'Outremers360 p{page}',
            'url': url,
            'mode': 'heading_links',
            'exclude_patterns': ['/category/', '/tag/', '/page/', '/author/'],
        })

    # ── Polynesie 1ere (France TV) ──
    sources.append({
        'name': 'Polynesie 1ere',
        'url': 'https://la1ere.francetvinfo.fr/polynesie/',
        'mode': 'heading_links',
        'exclude_patterns': ['/replay/', '/programme/', '/direct/'],
    })

    return sources


MAX_ARTICLES_PER_PAGE = 20  # Max liens par page source
MAX_TOTAL = 5               # Max articles publies par clic (leger et rapide)
REQUEST_TIMEOUT = 10
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'fr-FR,fr;q=0.9',
}

# ── Mots-cles pour le tri automatique ─────────────────────────────────────────

PROMO_KEYWORDS = [
    # Prix et reductions (score fort)
    r'-\d+\s*%', r'\d+\s*%\s*(de\s+)?(reduction|remise|rabais)',
    r'promo', r'promotion', r'solde', r'destockage',
    r'bon\s+plan', r'bons?\s+plans?', r'offre\s+speciale',
    r'prix\s+(casse|choc|bas|reduit|exceptionnel)',
    r'reduction', r'remise', r'rabais',
    r'vente\s+flash', r'liquidation',
    r'tarif\s+(preferen|reduit|promo)',
    # Enseignes et commerces polynesiens
    r'carrefour', r'champion', r'hyper\s*u', r'easy\s*market',
    r'electromenager', r'grande\s+surface',
    # Economie et consommation locale
    r'pouvoir\s+d.achat', r'inflation',
    r'hausse\s+des?\s+prix', r'baisse\s+des?\s+prix',
    r'cout\s+de\s+la\s+vie', r'panier\s+moyen',
    r'octroi\s+de\s+mer', r'tgc',
    r'import(ation)?\s+(de|des|alimentaire)',
    r'commerce\s+(local|exterieur)',
    r'marche\s+de\s+papeete', r'marche\s+municipal',
    # Emploi et salaires
    r'recrutement', r'embauche', r'offre\s+d.emploi',
    r'smic', r'salaire\s+minimum',
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
    # Projets et amenagement
    r'chantier', r'travaux', r'amenagement',
    r'projet\s+(urbain|immobilier|public)',
    r'construction', r'renovation',
    r'energie\s+(solaire|renouvelable|eolien)',
]


def _classify_article(title, content):
    """Classe un article en 'promo', 'nouveaute' ou 'info' selon son contenu."""
    text = f"{title} {content[:2000]}".lower()

    promo_score = 0
    for pattern in PROMO_KEYWORDS:
        if re.search(pattern, text, re.IGNORECASE):
            promo_score += 1

    nouveaute_score = 0
    for pattern in NOUVEAUTE_KEYWORDS:
        if re.search(pattern, text, re.IGNORECASE):
            nouveaute_score += 1

    if promo_score >= 2 and promo_score >= nouveaute_score:
        return 'promo'
    if nouveaute_score >= 2 and nouveaute_score > promo_score:
        return 'nouveaute'

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
            return ''
        from io import BytesIO
        from ads.image_utils import save_webp
        img_data = BytesIO(resp.content)
        img_data.name = 'download.jpg'
        img_data.size = len(resp.content)
        url = save_webp(img_data, 'rubriques', prefix)
        return url
    except Exception as e:
        logger.warning(f"Erreur photo {image_url[:50]}: {e}")
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
            links.append({
                'url': href, 'title': title,
                'source': source['name'],
                'force_category': source.get('force_category', ''),
            })

    return links[:MAX_ARTICLES_PER_PAGE]


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

    for tag in soup.select('script, style, nav, footer, header, aside, .sidebar, .menu, .ad, .comments'):
        tag.decompose()

    content_el = soup.select_one(
        'article, .article-content, .entry-content, .post-content, '
        '.content, main, .main-content, #content'
    )
    if not content_el:
        content_el = soup.body

    paragraphs = []
    if content_el:
        for p in content_el.select('p'):
            text = p.get_text(strip=True)
            if len(text) > 30:
                paragraphs.append(text)

    if not paragraphs and content_el:
        raw = content_el.get_text(separator='\n', strip=True)
        paragraphs = [line for line in raw.split('\n') if len(line.strip()) > 30]

    content = '\n\n'.join(paragraphs[:15])

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
    """Scrape les sources une par une, s'arrete des que MAX_TOTAL articles sont publies."""
    from .models import ArticleInfo, ArticlePromo, ArticleNouveaute
    import random

    bot = get_or_create_bot_user()
    results = {'info': 0, 'promo': 0, 'nouveaute': 0}
    total = 0

    sources = _build_sources()
    # Melanger pour varier les sources a chaque clic
    random.shuffle(sources)

    for source in sources:
        if total >= MAX_TOTAL:
            break

        links = scrape_links(source)
        for link in links:
            if total >= MAX_TOTAL:
                break

            if _is_duplicate(link['url']):
                continue

            if dry_run:
                total += 1
                continue

            content, photo_url = scrape_article_content(link['url'])
            if not content or len(content) < 100:
                continue

            # Force category si la source l'impose, sinon classification auto
            if link.get('force_category'):
                category = link['force_category']
            else:
                category = _classify_article(link['title'], content)
            saved_photo = download_and_save_photo(photo_url, f'{category}_{results[category]}')

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
            else:
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

    logger.info(f"Termine: {results} (total={total})")
    return results
