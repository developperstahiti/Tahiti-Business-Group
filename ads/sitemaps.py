from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.utils.text import slugify
from .models import Annonce, CATEGORIES




class StaticSitemap(Sitemap):
    """Pages statiques publiques du site."""

    def items(self):
        # Pages avec des noms de routes Django
        named_pages = [
            ('index',              1.0, 'daily'),
            ('liste_annonces',     0.9, 'daily'),
            ('page_info',          0.7, 'daily'),
            ('page_business',      0.7, 'daily'),
            ('tarifs_pubs',        0.5, 'weekly'),
            ('mentions_legales',   0.3, 'monthly'),
            ('politique_confidentialite', 0.3, 'monthly'),
            ('cgu',                0.3, 'monthly'),
        ]
        return named_pages

    def location(self, item):
        name, _priority, _freq = item
        return reverse(name)

    def priority(self, item):
        _name, prio, _freq = item
        return prio

    def changefreq(self, item):
        _name, _prio, freq = item
        return freq


class CategorieSitemap(Sitemap):
    """Pages de categories (via query string, car pas de routes dediees)."""
    changefreq = 'daily'
    priority = 0.7

    def items(self):
        return [slug for slug, _label in CATEGORIES]

    def location(self, item):
        return f'{reverse("liste_annonces")}?categorie={item}'


class AnnonceSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.6
    limit = 1000

    def items(self):
        return Annonce.objects.filter(statut='actif').order_by('-created_at')[:5000]

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return obj.get_absolute_url()


class LocaliteCategorieSitemap(Sitemap):
    """Pages SEO locales /annonces/<categorie>/<commune>/ — uniquement les
    combinaisons (categorie, commune) qui ont au moins 1 annonce active."""

    changefreq = 'daily'
    priority = 0.8

    def items(self):
        valid_cats = {slug for slug, _label in CATEGORIES}
        # Récupère toutes les paires (categorie, commune) distinctes pour les
        # annonces actives, en ignorant les communes vides.
        pairs = (
            Annonce.objects
            .filter(statut='actif')
            .exclude(commune='')
            .values_list('categorie', 'commune')
            .distinct()
        )

        seen = set()
        results = []
        for cat, commune in pairs:
            if cat not in valid_cats or not commune:
                continue
            commune_slug = slugify(commune)
            if not commune_slug:
                continue
            key = (cat, commune_slug)
            if key in seen:
                continue
            seen.add(key)
            results.append(key)
        return results

    def location(self, item):
        cat, commune_slug = item
        return reverse('liste_par_ville', kwargs={'categorie': cat, 'commune': commune_slug})
