from .settings import *

# Production Settings for cPanel Deployment

# Security
DEBUG = False
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-change-this-to-a-random-string-in-production')

# Allowed Hosts - Replace with your actual subdomain
# Example: ALLOWED_HOSTS = ['university.yourdomain.com', 'www.university.yourdomain.com']
ALLOWED_HOSTS = ['*']  # Will be updated with actual subdomain after deployment

# Database - MySQL for production
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get('DB_NAME', 'university_db'),
        'USER': os.environ.get('DB_USER', 'cp29524'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '3306'),
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# Static Files
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'public', 'static')

# Media Files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'public', 'media')

# Security Settings
SECURE_SSL_REDIRECT = False  # Set to True after SSL is configured
SESSION_COOKIE_SECURE = False  # Set to True after SSL is configured
CSRF_COOKIE_SECURE = False  # Set to True after SSL is configured
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = f'دانشگاه جامع <{os.environ.get("EMAIL_HOST_USER", "")}>'

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'django.log'),
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': True,
        },
    },
}
