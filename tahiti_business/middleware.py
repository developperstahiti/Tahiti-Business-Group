class SecurityHeadersMiddleware:
    """Ajoute des headers de securite HTTP a chaque reponse."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
            "https://cdn.tailwindcss.com https://static.osb.pf; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: blob: https://*.amazonaws.com; "
            "connect-src 'self'; "
            "frame-ancestors 'none'"
        )
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        response['X-Permitted-Cross-Domain-Policies'] = 'none'
        return response


# URL prefixes that correspond to private / authenticated pages.
_PRIVATE_PREFIXES = (
    '/deposer/',
    '/mes-',
    '/tbg-gestion-2026',
    '/users/',
    '/edit/',
    '/supprimer/',
    '/contact-modal/',
    '/signaler/',
    '/pubs/deposer/',
    '/rubriques/deposer/',
    '/rubriques/moderation/',
)


class NoCacheHTMLMiddleware:
    """Ajoute Cache-Control: no-cache uniquement sur les pages privees.

    Les pages publiques (accueil, liste annonces, detail, info, etc.)
    ne recoivent plus de no-cache afin de permettre le cache navigateur
    et un meilleur SEO.
    Les fichiers statiques (WhiteNoise) gardent leur propre cache policy.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        content_type = response.get('Content-Type', '')
        if 'text/html' in content_type and self._is_private(request.path):
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        return response

    @staticmethod
    def _is_private(path):
        return any(path.startswith(prefix) for prefix in _PRIVATE_PREFIXES)
