"""
Production settings for cPanel.

On server:
  DJANGO_SETTINGS_MODULE=config.settings_prod
"""

from pathlib import Path
import os

from decouple import config, Csv

from .settings import *  # noqa: F403,F401

BASE_DIR = Path(__file__).resolve().parent.parent

# -----------------------------------------------------------------------------
# Security
# -----------------------------------------------------------------------------
DEBUG = config('DEBUG', default=False, cast=bool)
SECRET_KEY = config('SECRET_KEY')
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='', cast=Csv())

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=False, cast=bool)
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=False, cast=bool)
CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=False, cast=bool)

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

# -----------------------------------------------------------------------------
# Database (default sqlite for local/dev fallback)
# -----------------------------------------------------------------------------
DB_ENGINE = config('DB_ENGINE', default='sqlite')

if DB_ENGINE == 'postgres':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME'),
            'USER': config('DB_USER'),
            'PASSWORD': config('DB_PASSWORD'),
            'HOST': config('DB_HOST', default='127.0.0.1'),
            'PORT': config('DB_PORT', default='5432'),
            'CONN_MAX_AGE': config('DB_CONN_MAX_AGE', default=60, cast=int),
        }
    }
elif DB_ENGINE == 'mysql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': config('DB_NAME'),
            'USER': config('DB_USER'),
            'PASSWORD': config('DB_PASSWORD'),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='3306'),
            # بدون این، هر درخواست یک اتصال تازه به MySQL باز و بسته
            # می‌کند. روی هاست اشتراکی که max_connections معمولاً ۲۵ تا
            # ۵۰ است، زیر بار به «Too many connections» می‌خورد.
            'CONN_MAX_AGE': config('DB_CONN_MAX_AGE', default=60, cast=int),
            'OPTIONS': {
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
                'charset': 'utf8mb4',
            },
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# -----------------------------------------------------------------------------
# Static & Media for cPanel
# -----------------------------------------------------------------------------
STATIC_URL = '/static/'
STATIC_ROOT = config('STATIC_ROOT', default=str(BASE_DIR / 'public' / 'static'))

MEDIA_URL = '/media/'
MEDIA_ROOT = config('MEDIA_ROOT', default=str(BASE_DIR / 'public' / 'media'))

# STATIC_ROOT را collectstatic می‌سازد، ولی MEDIA_ROOT را هیچ‌کس
# نمی‌ساخت: نه این فایل، نه deploy.py که پوشهٔ public را دست‌نخورده
# رد می‌کند. نتیجه‌اش این بود که اولین آپلود عکس در پنل ادمین به
# خطای ۵۰۰ می‌خورد، چون FileSystemStorage نمی‌توانست پوشهٔ مقصد را
# زیر یک والدِ ناموجود بسازد.
#
# شکستش عمداً بی‌صداست: این کد در زمان import تنظیمات اجرا می‌شود و
# یک استثنا اینجا یعنی کل سایت بالا نمی‌آید — که از خطای یک صفحه
# بدتر است. اگر مجوز نبود، diagnose.py دلیلش را می‌گوید.
try:
    os.makedirs(MEDIA_ROOT, exist_ok=True)
except OSError:
    pass

_static_dir = BASE_DIR / 'static'
STATICFILES_DIRS = [_static_dir] if _static_dir.exists() else []

# -----------------------------------------------------------------------------
# Email
# -----------------------------------------------------------------------------
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')

if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
    EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
    # پورت ۴۶۵ یعنی SSL و ۵۸۷ یعنی TLS. صندوق‌های cPanel معمولاً ۴۶۵
    # می‌دهند، پس پیش‌فرض از روی پورت حدس زده می‌شود تا کسی مجبور
    # نباشد هر دو کلید را دستی بنویسد. جنگو اگر هر دو True باشند
    # خطای «wrong version number» می‌دهد.
    EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=EMAIL_PORT == 465, cast=bool)
    EMAIL_USE_TLS = config(
        'EMAIL_USE_TLS', default=not EMAIL_USE_SSL, cast=bool)
    EMAIL_TIMEOUT = config('EMAIL_TIMEOUT', default=20, cast=int)
    DEFAULT_FROM_EMAIL = config(
        'DEFAULT_FROM_EMAIL',
        default=f'موسسه آموزش عالی علامه امینی <{EMAIL_HOST_USER}>',
    )
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    DEFAULT_FROM_EMAIL = 'موسسه آموزش عالی علامه امینی <noreply@localhost>'

PASSWORD_RESET_TIMEOUT = 3600

# -----------------------------------------------------------------------------
# SMS / OTP
# -----------------------------------------------------------------------------
SMS_ENABLED = config('SMS_ENABLED', default=False, cast=bool)
KAVENEGAR_API_KEY = config('KAVENEGAR_API_KEY', default='')
SMS_SENDER_NUMBER = config('SMS_SENDER_NUMBER', default='')
SMS_SITE_LABEL = config('SMS_SITE_LABEL', default='موسسه آموزش عالی علامه امینی')
PUBLIC_SITE_URL = config('PUBLIC_SITE_URL', default='https://portal.aab.ac.ir')
TUITION_INSTALLMENT_RATIOS = (
    config('TUITION_INSTALLMENT_R1', default=40, cast=int),
    config('TUITION_INSTALLMENT_R2', default=30, cast=int),
    config('TUITION_INSTALLMENT_R3', default=30, cast=int),
)
# نام الگوی تأیید (verify lookup) در پنل کاوه‌نگار؛ اگر پر باشد OTP از این روش ارسال می‌شود
KAVENEGAR_OTP_TEMPLATE = config('KAVENEGAR_OTP_TEMPLATE', default='')
OTP_SEND_COOLDOWN = config('OTP_SEND_COOLDOWN', default=60, cast=int)
OTP_MAX_SEND_PER_HOUR = config('OTP_MAX_SEND_PER_HOUR', default=5, cast=int)
OTP_MAX_VERIFY_ATTEMPTS = config('OTP_MAX_VERIFY_ATTEMPTS', default=5, cast=int)
# تأیید موبایل در محیط عملیاتی باید روشن بماند — با False هر کسی با هر شماره‌ای
# درخواست ثبت می‌کند و کل مرحلهٔ OTP بی‌اثر می‌شود.
ADMISSION_REQUIRE_MOBILE_OTP = config('ADMISSION_REQUIRE_MOBILE_OTP', default=True, cast=bool)

# Harden cookies further when SSL is on
if SECURE_SSL_REDIRECT:
    SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=31536000, cast=int)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
LOG_DIR = BASE_DIR / 'logs'
os.makedirs(LOG_DIR, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': str(LOG_DIR / 'django.log'),
            'formatter': 'verbose',
        },
        'console': {
            'level': 'ERROR',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'ERROR',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['file', 'console'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}
