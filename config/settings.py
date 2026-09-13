import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Security Settings
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')

DEBUG = os.getenv('DJANGO_DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost').split(',')
# Custom-domain stores are DB-backed, so Django's static ALLOWED_HOSTS cannot
# enumerate them. `*` is safe here because every request host is validated at
# runtime by CustomDomainRoutingMiddleware (unlisted hosts get a 400).
if '*' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('*')

CSRF_TRUSTED_ORIGINS = os.getenv('DJANGO_CSRF_TRUSTED_ORIGINS', 'http://127.0.0.1:8000,http://localhost:8000').split(',')


# Automated Custom Domain System (details: docs/custom_domains.md)
PLATFORM_DOMAIN = os.getenv('PLATFORM_DOMAIN', 'uddoktardokan.com')
SERVER_IP = os.getenv('SERVER_IP', '')
CUSTOM_DOMAIN_ENABLED = os.getenv('CUSTOM_DOMAIN_ENABLED', 'True') == 'True'
CUSTOM_DOMAIN_ALLOW_INTERNAL = os.getenv('CUSTOM_DOMAIN_ALLOW_INTERNAL', 'False') == 'True'
ACME_EMAIL = os.getenv('ACME_EMAIL', os.getenv('SSL_EMAIL', ''))
ACME_DIRECTORY_URL = os.getenv('ACME_DIRECTORY_URL', '')
SSL_WEBROOT = os.getenv('SSL_WEBROOT', str(BASE_DIR / 'ssl_webroot'))
CUSTOM_DOMAIN_CHECK_MINUTES = int(os.getenv('CUSTOM_DOMAIN_CHECK_MINUTES', '5'))
CUSTOM_DOMAIN_RENEW_DAYS = int(os.getenv('CUSTOM_DOMAIN_RENEW_DAYS', '30'))


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'rest_framework',
    'corsheaders',
    'django_filters',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.facebook',
    'store',
]

SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = 'optional'
ACCOUNT_LOGIN_METHODS = {'username', 'email'}
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_LOGOUT_ON_GET = True
SOCIALACCOUNT_LOGIN_ON_GET = True

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    # Runs after auth so the storefront rendered on a custom domain root has
    # request.user; and before CSRF so form POSTs on custom domains (cart,
    # checkout, wishlist...) validate against their own Origin.
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'store.middleware.CustomDomainRoutingMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'store.context_processors.site_info',
                'store.context_processors.cart_count',
                'store.context_processors.nav_menu',
                'store.context_processors.store_brand',
                'store.context_processors.category_menu',
                'store.context_processors.wallet_balance',
                'store.context_processors.wishlist_count',
                'store.context_processors.unread_notifications',
                'store.context_processors.wishlist_compare_ids',
                'store.context_processors.recently_viewed_products',
                'store.context_processors.page_settings',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database Configuration
# Dynamically connects to Managed PostgreSQL on Defang cloud, or drops back to local SQLite for local testing
DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
            'OPTIONS': {
                'timeout': 20,
            },
        }
    }


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# Static and Media Files Delivery (Updated for dynamic cloud media compatibility)
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Uses CompressedStaticFilesStorage to fix the WhiteNoise conflict with your URLs media server routing
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

# Media routing for banner and product image file uploads
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'

# Security Overrides for Cloud SSL/HTTPS Production
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    CSRF_COOKIE_HTTPONLY = True
    SESSION_COOKIE_HTTPONLY = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True

# Site Contact Information
SITE_PHONE = '01910422200'
SITE_WHATSAPP = '8801910422200'
SITE_ADDRESS_US = 'Delwar,USA'
SITE_ADDRESS_BD = '144/G,Zigatola(Near BGB Pilkhana)Mirpur-1,Dhaka:1206'
SITE_FACEBOOK = 'https://www.facebook.com/uddoktarbazaresdp'
SITE_YOUTUBE = 'https://www.youtube.com/@uddoktertbazartv'

# CORS Settings
CORS_ALLOWED_ORIGINS = CSRF_TRUSTED_ORIGINS
CORS_ALLOW_CREDENTIALS = True

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticatedOrReadOnly'],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
}

# Rate Limiting Engine
RATELIMIT_ENABLE = True
RATELIMIT_VIEW = 'store.views.ratelimit_error'

# SMTP Outbound Email Services
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', '')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@uddoktardokan.com')

# Caching Infrastructure (Automated fallback to system memory inside playground fallback logs)
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
if REDIS_URL and not DEBUG:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': REDIS_URL,
        }
    }
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }

# Celery Task Micro-Queues & Schedules
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', os.getenv('REDIS_URL', 'redis://localhost:6379/1'))
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
if DEBUG:
    CELERY_TASK_ALWAYS_EAGER = True

CELERY_BEAT_SCHEDULE = {
    'check-abandoned-carts': {
        'task': 'store.tasks.check_abandoned_carts',
        'schedule': 14400,
    },
    'cleanup-expired-carts': {
        'task': 'store.tasks.cleanup_expired_carts',
        'schedule': 86400,
    },
    'expire-expired-trials': {
        'task': 'store.tasks.expire_expired_trials',
        'schedule': 43200,
    },
    'expire-expired-active-subscriptions': {
        'task': 'store.tasks.expire_expired_active_subscriptions',
        'schedule': 43200,
    },
    'check-custom-domains': {
        'task': 'store.tasks.check_custom_domains_task',
        'schedule': 300.0,
    },
    'renew-custom-domain-certificates': {
        'task': 'store.tasks.renew_custom_domain_certificates',
        'schedule': 86400.0,
    },
}

# Administrative Systems Messaging 
ADMIN_BANNER_MESSAGE = ''

# SSLCommerz Payment Core Handlers
SSLCOMMERZ_STORE_ID = os.getenv('SSLCOMMERZ_STORE_ID', '')
SSLCOMMERZ_STORE_PASS = os.getenv('SSLCOMMERZ_STORE_PASS', '')
SSLCOMMERZ_IS_SANDBOX = os.getenv('SSLCOMMERZ_IS_SANDBOX', 'True') == 'True'
if SSLCOMMERZ_IS_SANDBOX:
    SSLCOMMERZ_API_URL = 'https://sandbox.sslcommerz.com/gwprocess/v4/api.php'
    SSLCOMMERZ_API_VALIDATION = 'https://sandbox.sslcommerz.com/validator/api/validationserverAPI.php'
else:
    SSLCOMMERZ_API_URL = 'https://secure.sslcommerz.com/gwprocess/v4/api.php'
    SSLCOMMERZ_API_VALIDATION = 'https://secure.sslcommerz.com/validator/api/validationserverAPI.php'

# Updated Structural Log Trackers for Containerized Cloud Environments
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'store': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
