import os
import time
from pathlib import Path
import dj_database_url
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Securite ───────────────────────────────────────────────────────────────────
_secret_key = os.environ.get('SECRET_KEY', '')
if not _secret_key:
    if os.environ.get('DATABASE_URL'):
        raise RuntimeError(
            "La variable d'environnement SECRET_KEY doit être définie en production !"
        )
    _secret_key = 'dev-only-insecure-key-ne-pas-utiliser-en-production'
SECRET_KEY = _secret_key

# En l'absence de DATABASE_URL on est en local (SQLite)
_local = not os.environ.get('DATABASE_URL')

DEBUG = os.environ.get('DEBUG', 'True' if _local else 'False') == 'True'

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')
ALLOWED_HOSTS = [h.strip() for h in ALLOWED_HOSTS if h.strip()]
if _local and not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]']

CSRF_TRUSTED_ORIGINS = os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',')
CSRF_TRUSTED_ORIGINS = [o.strip() for o in CSRF_TRUSTED_ORIGINS if o.strip()]

# Railway envoie les requetes en HTTP en interne, mais le header X-Forwarded-Proto indique HTTPS
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# ── Applications ───────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'ads',
    'users',
    'pubs',
    'rubriques',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'tahiti_business.middleware.NoCacheHTMLMiddleware',
]

# Autoriser l'affichage en iframe depuis n'importe quel site
# ⚠ SEO : ALLOWALL est necessaire pour l'embedding iframe des pubs.
#   Passer a 'SAMEORIGIN' si l'embedding externe n'est plus requis.
X_FRAME_OPTIONS = 'ALLOWALL'

# Taille max des uploads (50 Mo pour 5 photos de 10 Mo)
DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800  # 50 Mo
FILE_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10 Mo

ROOT_URLCONF = 'tahiti_business.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'pubs.context_processors.sidebar_pubs',
                'pubs.context_processors.admin_stats',
                'tahiti_business.context_processors.static_version',
            ],
        },
    },
]

WSGI_APPLICATION = 'tahiti_business.wsgi.application'

# ── Base de donnees ────────────────────────────────────────────────────────────
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(default=DATABASE_URL, conn_max_age=600)
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_USER_MODEL = 'users.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
]

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Pacific/Tahiti'
USE_I18N = True
USE_TZ = True

# ── Fichiers statiques (WhiteNoise) ───────────────────────────────────────────
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Version hash pour cache-busting (généré au démarrage = unique par déploiement)
STATIC_VERSION = str(int(time.time()))

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/users/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# ── Security headers ─────────────────────────────────────────────────────────
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# ── Email — Brevo (ex-Sendinblue) SMTP ──
_BREVO_USER = config('BREVO_USER', default='')
_BREVO_KEY  = config('BREVO_API_KEY', default='')
if _BREVO_USER and _BREVO_KEY:
    EMAIL_BACKEND       = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST          = 'smtp-relay.brevo.com'
    EMAIL_PORT          = 465
    EMAIL_USE_SSL       = True
    EMAIL_HOST_USER     = _BREVO_USER
    EMAIL_HOST_PASSWORD = _BREVO_KEY
else:
    # Pas de credentials Brevo → log en console (evite le crash)
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
EMAIL_TIMEOUT      = 10  # secondes — evite le blocage infini
DEFAULT_FROM_EMAIL = 'Tahiti Business Group <noreply@tahitibusinessgroup.com>'
SERVER_EMAIL       = 'noreply@tahitibusinessgroup.com'

# ── Anthropic (Claude AI) ──
ANTHROPIC_API_KEY = config('ANTHROPIC_API_KEY', default='')

# ── AWS S3 (stockage persistant sur Railway) ──────────────────────────────────
# Variables à ajouter dans Railway → Settings → Variables :
#   AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_STORAGE_BUCKET_NAME, AWS_S3_REGION_NAME
AWS_ACCESS_KEY_ID      = os.environ.get('AWS_ACCESS_KEY_ID', '')
AWS_SECRET_ACCESS_KEY  = os.environ.get('AWS_SECRET_ACCESS_KEY', '')
AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME', '')
AWS_S3_REGION_NAME     = os.environ.get('AWS_S3_REGION_NAME', 'eu-north-1')

# ── PayZen by OSB (paiement en ligne) ─────────────────────────────────────────
# ⚠ NE PAS mettre les clés en dur ici — les définir dans Railway > Variables
PAYZEN_SHOP_ID     = os.environ.get('PAYZEN_SHOP_ID', '')
PAYZEN_KEY_TEST    = os.environ.get('PAYZEN_KEY_TEST', '')
PAYZEN_KEY_PROD    = os.environ.get('PAYZEN_KEY_PROD', '')
PAYZEN_MODE        = os.environ.get('PAYZEN_MODE', 'TEST')   # TEST ou PRODUCTION
PAYZEN_PAYMENT_URL = os.environ.get('PAYZEN_PAYMENT_URL', 'https://secure.osb.pf/vads-payment/')

# Clés API REST PayZen (formulaire embarqué)
PAYZEN_REST_API_PASSWORD_TEST = os.environ.get('PAYZEN_REST_API_PASSWORD_TEST', '')
PAYZEN_REST_API_PASSWORD_PROD = os.environ.get('PAYZEN_REST_API_PASSWORD_PROD', '')
PAYZEN_PUBLIC_KEY_TEST = os.environ.get('PAYZEN_PUBLIC_KEY_TEST', '')
PAYZEN_PUBLIC_KEY_PROD = os.environ.get('PAYZEN_PUBLIC_KEY_PROD', '')
PAYZEN_HMAC_KEY_TEST = os.environ.get('PAYZEN_HMAC_KEY_TEST', '')
PAYZEN_HMAC_KEY_PROD = os.environ.get('PAYZEN_HMAC_KEY_PROD', '')
