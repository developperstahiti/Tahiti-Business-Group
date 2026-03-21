"""
Agents automatiques de scraping pour les rubriques TBG.

Scrape des sources polynesiennes et publie directement
dans ArticleInfo, ArticlePromo, ArticleNouveaute.
"""
import logging
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model

logger = logging.getLogger('rubriques.agents')

User = get_user_model()

# ── Sources par type de rubrique ──────────────────────────────────────────────

SOURCES_INFO = [
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
]

SOURCES_PROMO = [
    {
        'name': 'Tahiti Infos Eco',
        'url': 'https://www.tahiti-infos.com/Economie_r4.html',
        'mode': 'heading_links',
        'exclude_patterns': ['/404'],
    },
]

SOURCES_NOUVEAUTE = [
    {
        'name': 'Radio1 Actu',
        'url': 'https://www.radio1.pf/category/actus/',
        'mode': 'heading_links',
        'exclude_patterns': ['/event/', '/category/', '/page/', '/tag/'],
    },
]

MAX_ARTICLES_PER_SOURCE = 5
REQUEST_TIMEOUT = 15
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (compatible; TBG-Bot/1.0; +https://www.tahitibusinessgroup.com)',
    'Accept-Language': 'fr-FR,fr;q=0.9',
}


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
                links.append({'url': href, 'title': title})
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
                links.append({'url': href, 'title': title})

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
        # Garder les lignes de plus de 30 chars
        paragraphs = [line for line in raw.split('\n') if len(line.strip()) > 30]

    content = '\n\n'.join(paragraphs[:15])  # Max 15 paragraphes

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


def run_info_agent(dry_run=False):
    """Agent Info: scrape les actualites polynesiennes."""
    from .models import ArticleInfo
    bot = get_or_create_bot_user()
    created_count = 0

    for source in SOURCES_INFO:
        links = scrape_links(source)
        for link in links:
            if ArticleInfo.objects.filter(source_media=link['url']).exists():
                continue

            if dry_run:
                logger.info(f"[DRY RUN] Info: {link['title'][:60]}")
                created_count += 1
                if created_count >= MAX_ARTICLES_PER_SOURCE:
                    break
                continue

            content, photo_url = scrape_article_content(link['url'])
            if not content or len(content) < 100:
                logger.warning(f"[Info] Contenu trop court, ignore: {link['url']}")
                continue

            saved_photo = download_and_save_photo(photo_url, f'info_{created_count}')

            ArticleInfo.objects.create(
                auteur=bot,
                titre=link['title'][:200],
                contenu=content,
                photo=saved_photo,
                source_media=link['url'],
                statut='valide',
            )
            created_count += 1
            logger.info(f"[Info] Publie: {link['title'][:60]}")

            if created_count >= MAX_ARTICLES_PER_SOURCE:
                break

    return created_count


def run_promo_agent(dry_run=False):
    """Agent Promo: scrape les actus economiques."""
    from .models import ArticlePromo
    bot = get_or_create_bot_user()
    created_count = 0

    for source in SOURCES_PROMO:
        links = scrape_links(source)
        for link in links:
            if ArticlePromo.objects.filter(lien_promo=link['url']).exists():
                continue

            if dry_run:
                logger.info(f"[DRY RUN] Promo: {link['title'][:60]}")
                created_count += 1
                if created_count >= MAX_ARTICLES_PER_SOURCE:
                    break
                continue

            content, photo_url = scrape_article_content(link['url'])
            if not content or len(content) < 50:
                continue

            saved_photo = download_and_save_photo(photo_url, f'promo_{created_count}')

            ArticlePromo.objects.create(
                pro_user=bot,
                titre=link['title'][:200],
                contenu=content,
                photo=saved_photo,
                lien_promo=link['url'],
                statut='valide',
            )
            created_count += 1
            logger.info(f"[Promo] Publie: {link['title'][:60]}")

            if created_count >= MAX_ARTICLES_PER_SOURCE:
                break

    return created_count


def run_nouveaute_agent(dry_run=False):
    """Agent Nouveaute: scrape les infos locales."""
    from .models import ArticleNouveaute
    bot = get_or_create_bot_user()
    created_count = 0

    for source in SOURCES_NOUVEAUTE:
        links = scrape_links(source)
        for link in links:
            if ArticleNouveaute.objects.filter(lien_redirection=link['url']).exists():
                continue

            if dry_run:
                logger.info(f"[DRY RUN] Nouveaute: {link['title'][:60]}")
                created_count += 1
                if created_count >= MAX_ARTICLES_PER_SOURCE:
                    break
                continue

            content, photo_url = scrape_article_content(link['url'])
            if not content or len(content) < 50:
                continue

            saved_photo = download_and_save_photo(photo_url, f'nouv_{created_count}')

            ArticleNouveaute.objects.create(
                pro_user=bot,
                titre=link['title'][:200],
                contenu=content,
                photo=saved_photo,
                lien_redirection=link['url'],
                statut='valide',
            )
            created_count += 1
            logger.info(f"[Nouveaute] Publie: {link['title'][:60]}")

            if created_count >= MAX_ARTICLES_PER_SOURCE:
                break

    return created_count


def run_all_agents(dry_run=False):
    """Lance les 3 agents sequentiellement."""
    results = {}
    results['info'] = run_info_agent(dry_run=dry_run)
    results['promo'] = run_promo_agent(dry_run=dry_run)
    results['nouveaute'] = run_nouveaute_agent(dry_run=dry_run)
    return results
