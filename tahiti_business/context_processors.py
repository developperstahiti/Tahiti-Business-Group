from django.conf import settings


def static_version(request):
    return {'STATIC_VERSION': getattr(settings, 'STATIC_VERSION', '')}


def csp_nonce(request):
    return {'csp_nonce': getattr(request, 'csp_nonce', '')}


def adsense(request):
    """Expose le Publisher ID AdSense + slot IDs dans tous les templates."""
    return {
        'ADSENSE_PUBLISHER_ID': getattr(settings, 'ADSENSE_PUBLISHER_ID', ''),
        'ADSENSE_SLOT_SIDEBAR': getattr(settings, 'ADSENSE_SLOT_SIDEBAR', ''),
        'ADSENSE_SLOT_STRIP':   getattr(settings, 'ADSENSE_SLOT_STRIP', ''),
        'ADSENSE_SLOT_INFEED':  getattr(settings, 'ADSENSE_SLOT_INFEED', ''),
        'ADSENSE_SLOT_DETAIL':  getattr(settings, 'ADSENSE_SLOT_DETAIL', ''),
    }
