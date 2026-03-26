from django.shortcuts import redirect
from django.contrib import messages as django_messages


class OTPAdminMiddleware:
    """Exige la vérification TOTP pour accéder à l'admin SI l'utilisateur a un device configuré.

    Si aucun device TOTP n'existe, l'accès admin est autorisé normalement
    (permet la configuration initiale du device depuis l'admin).
    """

    _ADMIN_PREFIX = '/tbg-gestion-2026/'
    _SKIP_PATHS = ('/tbg-gestion-2026/login/', '/tbg-gestion-2026/otp-verify/')

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith(self._ADMIN_PREFIX):
            if any(request.path.startswith(p) for p in self._SKIP_PATHS):
                return self.get_response(request)
            user = request.user
            if user.is_authenticated and user.is_staff:
                from django_otp import user_has_device
                if user_has_device(user, confirmed=True) and not request.session.get('otp_admin_verified'):
                    return redirect('/tbg-gestion-2026/otp-verify/?next=' + request.path)
        return self.get_response(request)


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
