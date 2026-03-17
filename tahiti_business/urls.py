import os
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve
from django.http import HttpResponse, FileResponse
from ads.views import sitemap_xml

handler404 = 'ads.views.custom_404'


def robots_txt(request):
    base = request.build_absolute_uri('/')
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin/\n"
        "Disallow: /admin-stats/\n"
        "Disallow: /rubriques/moderation/\n"
        f"Sitemap: {base}sitemap.xml\n"
    )
    return HttpResponse(content, content_type='text/plain')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('ads.urls')),
    path('users/', include('users.urls')),
    path('pubs/', include('pubs.urls')),
    path('rubriques/', include('rubriques.urls')),
    path('robots.txt', robots_txt),
    path('sitemap.xml', sitemap_xml),
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
