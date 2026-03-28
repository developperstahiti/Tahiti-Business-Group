from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Annonce


class StaticSitemap(Sitemap):
    changefreq = 'daily'
    priority = 0.8

    def items(self):
        return ['index', 'liste_annonces']

    def location(self, item):
        return reverse(item)


class AnnonceSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.6

    def items(self):
        return Annonce.objects.filter(statut='actif').order_by('-created_at')[:1000]

    def lastmod(self, obj):
        return obj.updated_at if hasattr(obj, 'updated_at') else obj.created_at

    def location(self, obj):
        return reverse('annonce_detail', args=[obj.pk])
