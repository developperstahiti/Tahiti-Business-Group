from django.conf import settings


def static_version(request):
    return {'STATIC_VERSION': getattr(settings, 'STATIC_VERSION', '')}


def csp_nonce(request):
    return {'csp_nonce': getattr(request, 'csp_nonce', '')}


def adsense(request):
    """Expose le Publisher ID AdSense dans tous les templates."""
    return {'ADSENSE_PUBLISHER_ID': getattr(settings, 'ADSENSE_PUBLISHER_ID', '')}
