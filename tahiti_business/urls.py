import os
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve
from django.http import HttpResponse, FileResponse
from django.shortcuts import render
from django.contrib.sitemaps.views import sitemap
from ads.sitemaps import StaticSitemap, CategorieSitemap, AnnonceSitemap
from two_factor.urls import urlpatterns as tf_urls

sitemaps = {
    'static': StaticSitemap,
    'categories': CategorieSitemap,
    'annonces': AnnonceSitemap,
}

admin.site.site_header = 'TBG Gestion'
admin.site.site_title = 'TBG Gestion'
admin.site.index_title = 'Tableau de bord'

handler404 = 'ads.views.custom_404'


def robots_txt(request):
    lines = [
        "User-agent: *",
        "Allow: /",
        "",
        "# Admin & back-office",
        "Disallow: /3319cdb9fc7eb59/",
        "Disallow: /admin/",
        "Disallow: /admin-stats/",
        "Disallow: /rubriques/moderation/",
        "",
        "# Espace utilisateur prive",
        "Disallow: /users/",
        "Disallow: /account/",
        "Disallow: /mon-compte/",
        "Disallow: /mes-annonces/",
        "Disallow: /mes-messages/",
        "Disallow: /mes-favoris/",
        "Disallow: /mes-alertes/",
        "",
        "# Depot & actions privees",
        "Disallow: /deposer/",
        "Disallow: /pubs/deposer/",
        "Disallow: /pubs/demande/",
        "Disallow: /pubs/paiement/",
        "Disallow: /rubriques/promo/deposer/",
        "Disallow: /rubriques/info/deposer/",
        "Disallow: /rubriques/nouveaute/deposer/",
        "Disallow: /annonces/import-url/",
        "Disallow: /annonces/toggle-enregistrement/",
        "Disallow: /boost/",
        "",
        "# Signalement",
        "Disallow: /signaler/",
        "",
        "# API internes",
        "Disallow: /api/",
        "Disallow: /rubriques/run-agents/",
        "",
        "Sitemap: https://www.tahitibusinessgroup.com/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


urlpatterns = [
    path('admin/<path:p>', lambda r, p=None: HttpResponse(status=404)),
    path('admin/', lambda r: HttpResponse(status=404)),
    path('3319cdb9fc7eb59/', admin.site.urls),
    path('', include(tf_urls)),
    path('', include('ads.urls')),
    path('users/', include('users.urls')),
    path('pubs/', include('pubs.urls')),
    path('rubriques/', include('rubriques.urls')),
    path('forum/', include('forum.urls')),
    path('robots.txt', robots_txt, name='robots_txt'),
    path('favicon.ico', lambda r: HttpResponse(status=301, headers={'Location': '/static/img/favicon-tbg-32.png'})),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('sw.js', lambda r: FileResponse(
        open(os.path.join(settings.STATIC_ROOT or os.path.join(settings.BASE_DIR, 'static'), 'sw.js'), 'rb'),
        content_type='application/javascript',
        headers={'Service-Worker-Allowed': '/', 'Cache-Control': 'no-cache'},
    ), name='service_worker'),
    path('offline.html', lambda r: render(r, 'offline.html')),
    path('manifest.json', lambda r: FileResponse(
        open(os.path.join(settings.STATIC_ROOT or os.path.join(settings.BASE_DIR, 'static'), 'manifest.json'), 'rb'),
        content_type='application/manifest+json',
    ), name='manifest'),
    path('.well-known/assetlinks.json', lambda r: HttpResponse(
        '[{"relation":["delegate_permission/common.handle_all_urls"],"target":{"namespace":"android_app","package_name":"com.tahitibusinessgroup.app","sha256_cert_fingerprints":["C6:A1:2A:8C:6B:40:2C:7C:FF:1C:1C:C6:2F:21:7D:1C:95:BE:E1:B2:DD:0C:9C:CE:49:8F:58:24:09:FB:6A:F6"]}}]',
        content_type='application/json',
    )),
]

# Serve media files in all environments (DEBUG=True and DEBUG=False)
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]
