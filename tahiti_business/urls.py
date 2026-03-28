import os
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve
from django.http import HttpResponse, FileResponse
from django.contrib.sitemaps.views import sitemap
from ads.sitemaps import StaticSitemap, AnnonceSitemap
from two_factor.urls import urlpatterns as tf_urls

sitemaps = {
    'static': StaticSitemap,
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
        "Disallow: /3319cdb9fc7eb59/",
        "Disallow: /admin-stats/",
        "Disallow: /deposer/",
        "Disallow: /mes-annonces/",
        "Disallow: /mes-messages/",
        "Disallow: /mes-favoris/",
        "Disallow: /mon-compte/",
        "Disallow: /users/",
        "Disallow: /signaler/",
        "Disallow: /pubs/deposer/",
        "Disallow: /rubriques/moderation/",
        "Disallow: /account/",
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
    path('robots.txt', robots_txt, name='robots_txt'),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('sw.js', lambda r: FileResponse(
        open(os.path.join(settings.STATIC_ROOT or os.path.join(settings.BASE_DIR, 'static'), 'sw.js'), 'rb'),
        content_type='application/javascript',
        headers={'Service-Worker-Allowed': '/', 'Cache-Control': 'no-cache'},
    ), name='service_worker'),
    path('manifest.json', lambda r: FileResponse(
        open(os.path.join(settings.STATIC_ROOT or os.path.join(settings.BASE_DIR, 'static'), 'manifest.json'), 'rb'),
        content_type='application/manifest+json',
    ), name='manifest'),
]

# Serve media files in all environments (DEBUG=True and DEBUG=False)
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]
