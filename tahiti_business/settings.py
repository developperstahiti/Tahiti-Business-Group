import os
import time
from pathlib import Path
import dj_database_url
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Securite ───────────────────────────────────────────────────────────────────
SECRET_KEY = config('SECRET_KEY', default='dev-only-insecure-key-ne-pas-utiliser-en-production')

# En l'absence de DATABASE_URL on est en local (SQLite)
_local = not os.environ.get('DATABASE_URL')

DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1,[::1]').split(',')
ALLOWED_HOSTS = [h.strip() for h in ALLOWED_HOSTS if h.strip()]

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
    'django_otp',
    'django_otp.plugins.otp_totp',
    'django_otp.plugins.otp_static',
    'two_factor',
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
    'django_otp.middleware.OTPMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'tahiti_business.middleware.SecurityHeadersMiddleware',
    'tahiti_business.middleware.NoCacheHTMLMiddleware',
]

X_FRAME_OPTIONS = 'DENY'

# Taille max des uploads (50 Mo pour 5 photos de 5 Mo + champs)
DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800  # 50 Mo
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5 Mo

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
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
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

# ── 2FA (django-two-factor-auth) — admin uniquement ──
TWO_FACTOR_PATCH_ADMIN = True
TWO_FACTOR_LOGIN_TIMEOUT = 600  # 10 min pour saisir le code

# ── Security headers ─────────────────────────────────────────────────────────
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True

# Cookies sécurisés (production)
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'

# Expiration session après 30 min d'inactivité
SESSION_COOKIE_AGE = 1800
SESSION_SAVE_EVERY_REQUEST = True

# ── Email — Brevo API HTTP (SMTP bloque par Railway) ──
BREVO_API_V3_KEY = config('BREVO_API_V3_KEY', default='')
if BREVO_API_V3_KEY:
    EMAIL_BACKEND = 'tahiti_business.brevo_backend.BrevoAPIBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
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
