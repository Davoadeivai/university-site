# 🚀 راهنمای Deploy روی Render

## مرحله ۱: آماده‌سازی Repository

تمام فایل‌های ضروری در این branch موجود هستند:
- ✅ `build.sh` - دستورات build
- ✅ `runtime.txt` - نسخه Python
- ✅ `requirements.txt` - dependencies
- ✅ `.env.example` - متغیرهای محیطی
- ✅ `render.yaml` - تنظیمات Render

## مرحله ۲: تنظیمات Settings برای Production

فایل `config/settings.py` را طبق زیر تغییر دهید:

```python
import os
from decouple import config

# Security Settings
DEBUG = config('DEBUG', default=False, cast=bool)
SECRET_KEY = config('SECRET_KEY', default='fallback-key')
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost').split(',')

# Database Configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='university_db'),
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

# Static Files
STATIC_URL = '/static/'
STATIC_ROOT = '/var/data/staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = f'دانشگاه جامع <{EMAIL_HOST_USER}>'
```

### تغییرات Middleware:

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # ✅ اضافه شد
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```

## مرحله ۳: ایجاد Render Service

1. به [render.com](https://render.com) بروید و لاگین کنید
2. **New +** → **Web Service**
3. **Connect Repository:** `Davoadeivai/university-site`
4. تنظیمات:
   - **Name:** `university-site`
   - **Runtime:** `Python`
   - **Build Command:** `cd university_site && bash build.sh`
   - **Start Command:** `cd university_site && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`

## مرحله ۴: Environment Variables

در داشبورد Render، این متغیرها را اضافه کنید:

| Key | Value | تولید کردن |
|-----|-------|----------|
| `SECRET_KEY` | [کلید رندم] | `python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'` |
| `DEBUG` | `False` | - |
| `ALLOWED_HOSTS` | `your-app.onrender.com` | - |
| `DATABASE_URL` | [از PostgreSQL] | ✅ خودکار |
| `EMAIL_HOST_USER` | [Gmail address] | - |
| `EMAIL_HOST_PASSWORD` | [App Password] | [مراحل زیر] |

### دریافت Google App Password:

1. [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) باز کنید
2. Select app: **Mail**
3. Select device: **Windows Computer** (یا دستگاه خود)
4. **Generate** را کلیک کنید
5. Password 16 کاراکتری را کپی کنید

## مرحله ۵: Database Connection

Render PostgreSQL رایگان ارائه می‌دهد:

1. در Render dashboard، **New +** → **PostgreSQL**
2. تنظیمات:
   - **Name:** `university-db`
   - **Database:** `university_db`
   - **Username:** `postgres`
3. **Create** کلیک کنید
4. CONNECTION STRING را کپی کنید
5. در Web Service، `DATABASE_URL` را با این string تنظیم کنید

## مرحله ۶: Deploy و Testing

```bash
# بعد از Deploy موفق:

# 1. Database Migrations
render exec python manage.py migrate

# 2. Create Superuser
render exec python manage.py createsuperuser

# 3. Static Files
render exec python manage.py collectstatic --noinput
```

## ⚠️ مشکلات رایج و حل‌ها

### Static Files 404
```bash
# Rebuild کنید
rm -rf staticfiles/ && python manage.py collectstatic --noinput
```

### Database Connection Error
```bash
# تأکید کنید DATABASE_URL صحیح است
echo $DATABASE_URL
```

### Email نمی‌رسد
- Gmail 2FA فعال کنید
- App Password استفاده کنید (نه رمز عبور اصلی)

### 500 Error
- `DEBUG=True` موقتاً بگذارید
- Render Logs را بررسی کنید

## ✅ Checklist

- [ ] تمام فایل‌های deployment موجود هستند
- [ ] `settings.py` برای production آماده است
- [ ] `requirements.txt` تمام packages را دارد
- [ ] Repository به Render متصل است
- [ ] PostgreSQL ایجاد شد
- [ ] Environment variables تنظیم شده‌اند
- [ ] Build command موفق اجرا شد
- [ ] Database migrations انجام شد
- [ ] Superuser ایجاد شد
- [ ] سایت در `https://your-app.onrender.com` قابل دسترسی است

## 🔗 منابع مفید

- [Render Django Docs](https://render.com/docs/deploy-django)
- [Django Production Checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/)
- [Whitenoise Documentation](http://whitenoise.evans.io/)
- [PostgreSQL on Render](https://render.com/docs/postgres)

---

**نکات مهم:**

1. هرگز `SECRET_KEY` را در Repository commit نکنید
2. `DEBUG` را همیشه `False` نگه دارید در Production
3. HTTPS خودکار است روی Render
4. Media files نیاز به S3 یا CDN دارند (برای اپلیکیشن بزرگ‌تر)

**اگر مشکلی داشتید، Render Support را چک کنید یا لاگ‌های deployment را بررسی کنید!** 🚀
