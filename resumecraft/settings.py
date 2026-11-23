"""
Django settings for ResumeCraft AI project.

IMPORTANT ARCHITECTURE NOTE:
This project is deliberately designed to be 100% DATABASE-FREE.
- No SQLite, PostgreSQL, MySQL or MongoDB.
- All user data persists securely in the client's browser localStorage.
- Django functions strictly as a secure API gateway, template renderer,
  and static file server.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv(
    'SECRET_KEY',
    'django-insecure-resumecraft-ai-super-secret-key-for-local-development-change-in-prod'
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 't', 'yes')

# Allowed Hosts configuration
# In production, Render assigns dynamic hostnames (e.g. *.onrender.com).
# We allow wildcard '*', '.onrender.com', local dev hosts, and dynamic Render hostnames.
ALLOWED_HOSTS = ['*', '.onrender.com', 'localhost', '127.0.0.1', 'testserver']

render_hostname = os.getenv('RENDER_EXTERNAL_HOSTNAME')
if render_hostname and render_hostname not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(render_hostname)

custom_hosts = os.getenv('ALLOWED_HOSTS', '')
if custom_hosts:
    for host in custom_hosts.split(','):
        h = host.strip()
        if h and h not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(h)

# Reverse proxy SSL header for Render / cloud deployments
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Application definition
# Deliberately omitting all database-dependent apps:
# (NO django.contrib.admin, auth, contenttypes, sessions, messages)
INSTALLED_APPS = [
    'whitenoise.runserver_nostatic',
    'django.contrib.staticfiles',
    'builder',
]

# Deliberately omitting database-dependent middlewares:
# (NO SessionMiddleware, AuthenticationMiddleware, MessageMiddleware)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'resumecraft.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
            ],
        },
    },
]

WSGI_APPLICATION = 'resumecraft.wsgi.application'

# ==============================================================================
# ABSOLUTELY NO DATABASE
# Empty DATABASES dictionary ensures Django will never attempt to connect,
# create tables, or perform migrations.
# ==============================================================================
DATABASES = {}

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise storage configuration for high-performance static delivery
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
    },
}

# CSRF configuration for local and Render production
CSRF_TRUSTED_ORIGINS = [
    'https://*.onrender.com',
    'https://*.render.com',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]
if render_hostname:
    CSRF_TRUSTED_ORIGINS.append(f'https://{render_hostname}')

custom_csrf = os.getenv('CSRF_TRUSTED_ORIGINS', '')
if custom_csrf:
    for origin in custom_csrf.split(','):
        o = origin.strip()
        if o and o not in CSRF_TRUSTED_ORIGINS:
            CSRF_TRUSTED_ORIGINS.append(o)

# Security Settings for Production
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    CSRF_COOKIE_SECURE = True

# Gemini API Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
