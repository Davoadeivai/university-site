from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

# -----------------------------------------------------------------------------
# Core
# -----------------------------------------------------------------------------
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

# -----------------------------------------------------------------------------
# Apps
# -----------------------------------------------------------------------------
INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'crispy_forms',
    'crispy_bootstrap5',
    'core.apps.CoreConfig',
    'accounts.apps.AccountsConfig',
    'news.apps.NewsConfig',
    'academics.apps.AcademicsConfig',
    'faculty.apps.FacultyConfig',
    'research.apps.ResearchConfig',
    'library.apps.LibraryConfig',
    'admissions.apps.AdmissionsConfig',
    'contact.apps.ContactConfig',
    'dashboard.apps.DashboardConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'core.middleware.ForcePersianMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
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
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.i18n',
                'core.context_processors.global_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# -----------------------------------------------------------------------------
# Database: sqlite | postgres | mysql
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
# Password validation
# -----------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# -----------------------------------------------------------------------------
# i18n
# -----------------------------------------------------------------------------
LANGUAGE_CODE = 'fa'
TIME_ZONE = 'Asia/Tehran'
USE_I18N = True
USE_L10N = True
USE_TZ = True

LANGUAGES = [
    ('fa', 'فارسی'),
    ('en', 'English'),
]

LOCALE_PATHS = [BASE_DIR / 'locale']

# -----------------------------------------------------------------------------
# Static & Media (local)
# -----------------------------------------------------------------------------
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# -----------------------------------------------------------------------------
# Crispy
# -----------------------------------------------------------------------------
CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

# -----------------------------------------------------------------------------
# Auth
# -----------------------------------------------------------------------------
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'

# -----------------------------------------------------------------------------
# Jazzmin
# -----------------------------------------------------------------------------
JAZZMIN_SETTINGS = {
    'site_title': 'پنل مدیریت | علامه امینی',
    'site_header': 'موسسه آموزش عالی علامه امینی بهنمیر',
    'site_brand': 'علامه امینی',
    'welcome_sign': 'به پنل مدیریت موسسه خوش آمدید',
    'copyright': 'طراحی، اجرا و پشتیبانی توسط شرکت آرکاروناک — arkaronak.ir',
    'search_model': [
        'admissions.Application',
        'auth.User',
        'news.News',
        'academics.Major',
        'faculty.Professor',
    ],
    'topmenu_links': [
        {'name': 'مشاهده سایت', 'url': '/', 'new_window': True},
        {'name': 'داشبورد کاربران', 'url': '/dashboard/'},
        {'name': 'درخواست‌های پذیرش', 'url': 'admin:admissions_application_changelist'},
        {'name': 'پیام‌های تماس', 'url': 'admin:contact_contactmessage_changelist'},
    ],
    'show_sidebar': True,
    'navigation_expanded': True,
    # ترتیب نمایش بخش‌ها در صفحه اصلی ادمین
    'order_with_respect_to': [
        'core',
        'admissions',
        'academics',
        'faculty',
        'news',
        'library',
        'research',
        'dashboard',
        'accounts',
        'contact',
        'auth',
    ],
    'icons': {
        'auth': 'fas fa-users-cog',
        'auth.User': 'fas fa-user',
        'auth.Group': 'fas fa-users',

        'core': 'fas fa-globe',
        'core.SiteSettings': 'fas fa-cog',
        'core.Slider': 'fas fa-images',
        'core.QuickLink': 'fas fa-link',
        'core.Event': 'fas fa-calendar-alt',
        'core.FAQ': 'fas fa-question-circle',
        'core.PageView': 'fas fa-chart-line',
        'core.InstitutionGoal': 'fas fa-bullseye',
        'core.BoardMember': 'fas fa-user-tie',
        'core.CityInfo': 'fas fa-map-marker-alt',
        'core.CityAttraction': 'fas fa-camera',
        'core.PresidencyOffice': 'fas fa-landmark',
        'core.PresidencyOfficeUnit': 'fas fa-door-open',
        'core.GraduateStudiesInfo': 'fas fa-user-graduate',
        'core.DeputyVice': 'fas fa-user-friends',
        'core.InternationalOffice': 'fas fa-plane',
        'core.InternationalActivity': 'fas fa-handshake',
        'core.PublicRelations': 'fas fa-bullhorn',
        'core.PressRelease': 'fas fa-newspaper',
        'core.SecurityOffice': 'fas fa-shield-alt',
        'core.VicePresidency': 'fas fa-sitemap',
        'core.ViceUnit': 'fas fa-building',
        'core.ViceAchievement': 'fas fa-trophy',
        'core.OrganizationalChart': 'fas fa-project-diagram',
        'core.BankAccount': 'fas fa-university',
        'core.PaymentIdentifier': 'fas fa-barcode',
        'core.DownloadableDocument': 'fas fa-file-download',
        'core.PageView': 'fas fa-chart-line',

        'admissions': 'fas fa-user-graduate',
        'admissions.AdmissionInfo': 'fas fa-info-circle',
        'admissions.Application': 'fas fa-file-alt',
        'admissions.TuitionStructure': 'fas fa-money-bill-wave',
        'admissions.TuitionDiscount': 'fas fa-percent',
        'admissions.StudentPayment': 'fas fa-receipt',
        'admissions.AdmissionOTP': 'fas fa-sms',

        'academics': 'fas fa-graduation-cap',
        'academics.Department': 'fas fa-building',
        'academics.AcademicGroup': 'fas fa-layer-group',
        'academics.Major': 'fas fa-book-open',
        'academics.Course': 'fas fa-chalkboard',
        'academics.AcademicCalendar': 'fas fa-calendar',
        'academics.Laboratory': 'fas fa-flask',

        'faculty': 'fas fa-chalkboard-teacher',
        'faculty.Professor': 'fas fa-user-tie',
        'faculty.Publication': 'fas fa-book',

        'news': 'fas fa-newspaper',
        'news.Category': 'fas fa-tags',
        'news.News': 'fas fa-newspaper',
        'news.Gallery': 'fas fa-image',

        'library': 'fas fa-book-reader',
        'library.Book': 'fas fa-book',
        'library.Article': 'fas fa-file-alt',
        'library.LibraryMembership': 'fas fa-id-card',

        'research': 'fas fa-microscope',
        'research.ResearchProject': 'fas fa-flask',
        'research.Journal': 'fas fa-journal-whills',
        'research.Thesis': 'fas fa-scroll',
        'research.Conference': 'fas fa-users',
        'research.IndustryPartnership': 'fas fa-industry',

        'dashboard': 'fas fa-tachometer-alt',
        'dashboard.Semester': 'fas fa-calendar-check',
        'dashboard.Enrollment': 'fas fa-user-plus',
        'dashboard.TeachingAssignment': 'fas fa-tasks',
        'dashboard.StudentRequest': 'fas fa-envelope-open-text',
        'dashboard.Payment': 'fas fa-credit-card',
        'dashboard.ExamSchedule': 'fas fa-clock',
        'dashboard.Assignment': 'fas fa-clipboard-list',
        'dashboard.AssignmentSubmission': 'fas fa-upload',
        'dashboard.Attendance': 'fas fa-user-check',

        'accounts': 'fas fa-id-badge',
        'accounts.UserProfile': 'fas fa-address-card',
        'accounts.Announcement': 'fas fa-bell',
        'accounts.OTPCode': 'fas fa-key',

        'contact': 'fas fa-phone-alt',
        'contact.ContactMessage': 'fas fa-envelope',
        'contact.Alumni': 'fas fa-user-friends',
    },
    'default_icon_parents': 'fas fa-folder',
    'default_icon_children': 'fas fa-circle',
    'related_modal_active': True,
    'custom_css': 'admin/css/rtl_admin.css',
    'custom_js': 'admin/js/fa_admin.js',
    'show_ui_builder': False,
    'changeform_format': 'collapsible',
    'changeform_format_overrides': {
        # فرم اسناد باید تک‌صفحه‌ای باشد تا فیلدهای آپلود PDF/Word دیده شوند
        'core.downloadabledocument': 'single',
    },
    'language_chooser': False,
    # مدل‌های کم‌کاربرد/فنی — در صورت نیاز از URL مستقیم قابل دسترس‌اند
    'hide_models': [
        'core.PageView',
    ],
    'custom_links': {
        'admissions': [{
            'name': 'ثبت‌نام آنلاین (سایت)',
            'url': '/پذیرش/تایید-موبایل/',
            'icon': 'fas fa-external-link-alt',
            'new_window': True,
        }],
        'core': [
            {
                'name': 'صفحه اصلی سایت',
                'url': '/',
                'icon': 'fas fa-home',
                'new_window': True,
            },
            {
                'name': 'رشته‌های تحصیلات تکمیلی',
                'url': '/admin/academics/major/?degree__exact=master',
                'icon': 'fas fa-graduation-cap',
                'permissions': ['academics.view_major'],
            },
            {
                'name': 'آیین‌نامه‌های تحصیلات تکمیلی',
                'url': '/admin/core/downloadabledocument/?section__exact=graduate',
                'icon': 'fas fa-file-alt',
                'permissions': ['core.view_downloadabledocument'],
            },
        ],
        'academics': [{
            'name': 'فقط رشته‌های ارشد',
            'url': '/admin/academics/major/?degree__exact=master',
            'icon': 'fas fa-user-graduate',
            'permissions': ['academics.view_major'],
        }],
    },
}

JAZZMIN_UI_TWEAKS = {
    'navbar_small_text': False,
    'footer_small_text': False,
    'body_small_text': False,
    'brand_small_text': False,
    'brand_colour': 'navbar-primary',
    'accent': 'accent-primary',
    'navbar': 'navbar-dark',
    'no_navbar_border': False,
    'navbar_fixed': True,
    'layout_boxed': False,
    'footer_fixed': False,
    'sidebar_fixed': True,
    'sidebar': 'sidebar-dark-primary',
    'theme': 'default',
    'dark_mode_theme': None,
    'button_classes': {
        'primary': 'btn-primary',
        'secondary': 'btn-secondary',
        'info': 'btn-info',
        'warning': 'btn-warning',
        'danger': 'btn-danger',
        'success': 'btn-success',
    },
}

# -----------------------------------------------------------------------------
# Email
# -----------------------------------------------------------------------------
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')

if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
    EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
    EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
    DEFAULT_FROM_EMAIL = config(
        'DEFAULT_FROM_EMAIL',
        default=f'موسسه آموزش عالی علامه امینی بهنمیر <{EMAIL_HOST_USER}>',
    )
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    DEFAULT_FROM_EMAIL = 'موسسه آموزش عالی علامه امینی بهنمیر <noreply@localhost>'

PASSWORD_RESET_TIMEOUT = 3600

# -----------------------------------------------------------------------------
# SMS / OTP (Kavenegar)
# -----------------------------------------------------------------------------
SMS_ENABLED = config('SMS_ENABLED', default=False, cast=bool)
KAVENEGAR_API_KEY = config('KAVENEGAR_API_KEY', default='')
SMS_SENDER_NUMBER = config('SMS_SENDER_NUMBER', default='')
# پیشوند متن پیامک‌های اطلاع‌رسانی
SMS_SITE_LABEL = config('SMS_SITE_LABEL', default='موسسه آموزش عالی علامه امینی بهنمیر')
# نام الگوی تأیید (verify lookup) در پنل کاوه‌نگار؛ اگر پر باشد OTP از این روش ارسال می‌شود
KAVENEGAR_OTP_TEMPLATE = config('KAVENEGAR_OTP_TEMPLATE', default='')
OTP_SEND_COOLDOWN = config('OTP_SEND_COOLDOWN', default=60, cast=int)
OTP_MAX_SEND_PER_HOUR = config('OTP_MAX_SEND_PER_HOUR', default=5, cast=int)
OTP_MAX_VERIFY_ATTEMPTS = config('OTP_MAX_VERIFY_ATTEMPTS', default=5, cast=int)
# موقتاً False: مرحله تأیید موبایل پذیرش غیرفعال است (مستقیم فرم). برای فعال‌سازی دوباره True کنید.
ADMISSION_REQUIRE_MOBILE_OTP = config('ADMISSION_REQUIRE_MOBILE_OTP', default=False, cast=bool)

# -----------------------------------------------------------------------------
# Online payment (mock | zarinpal)
# -----------------------------------------------------------------------------
PAYMENT_GATEWAY = config('PAYMENT_GATEWAY', default='mock')  # mock | zarinpal
ZARINPAL_MERCHANT_ID = config('ZARINPAL_MERCHANT_ID', default='')
ZARINPAL_SANDBOX = config('ZARINPAL_SANDBOX', default=True, cast=bool)

# -----------------------------------------------------------------------------
# Cache (OTP rate limits)
# -----------------------------------------------------------------------------
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'university-otp',
    }
}
