# 🚂 Railway & Django - Production Deployment

## فهرست محتویات

1. [تغییرات انجام‌شده](#تغییرات-انجام‌شده)
2. [فایل‌های نصب‌شده](#فایل‌های-نصب‌شده)
3. [تنظیمات Production](#تنظیمات-production)
4. [مراحل Deploy](#مراحل-deploy)
5. [Troubleshooting](#troubleshooting)

---

## تغییرات انجام‌شده

### ✅ Settings برای Production

```python
# config/settings.py

# Security
SECRET_KEY = config('SECRET_KEY')  # از environment
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS').split(',')

# Database
if DEBUG:
    # SQLite (development)
    DATABASES = {'default': {'ENGINE': 'sqlite3', ...}}
else:
    # PostgreSQL (production)
    import dj_database_url
    DATABASES = {'default': dj_database_url.config(...)}

# Static Files + Whitenoise
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
MIDDLEWARE = ['whitenoise.middleware.WhiteNoiseMiddleware', ...]

# Security Headers
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

### ✅ Dependencies

```txt
Django==5.2.3
Gunicorn==21.2.0
Whitenoise==6.6.0
dj-database-url==2.1.0
psycopg2-binary==2.9.9
python-decouple==3.8
```

### ✅ Build Scripts

```bash
# Procfile
web: cd university_site && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT

# build.sh
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```

---

## فایل‌های نصب‌شده

### 📁 Configuration Files

| فایل | توضیح |
|------|-------|
| `config/settings.py` | Django settings برای production |
| `requirements.txt` | Python packages |
| `Procfile` | Railway process definition |
| `build.sh` | Build automation |
| `runtime.txt` | Python version (3.11.9) |
| `.env.example` | Environment variables template |
| `.gitignore` | Git ignore rules |

### 📁 Documentation Files

| فایل | توضیح |
|------|-------|
| `RAILWAY_SETUP_STEPS.md` | راهنمای جامع Railway (فارسی) |
| `RAILWAY_README.md` | Quick start guide |
| `DEPLOYMENT_CHECKLIST.md` | Deploy checklist |
| `TROUBLESHOOTING.md` | مشکل‌گیری |
| `deploy-helper.sh` | Helper script |

---

## تنظیمات Production

### 🔐 Security

✅ HTTPS (خودکار Railway)
✅ Secure Cookies
✅ CSRF Protection
✅ Security Headers
✅ XSS Filter

### 📦 Database

✅ PostgreSQL
✅ Connection pooling
✅ Health checks
✅ Auto-migration

### 📁 Static Files

✅ Whitenoise compression
✅ Manifest storage
✅ Cache busting
✅ CDN-ready

### 📧 Email

✅ Gmail SMTP
✅ Environment variables
✅ Console fallback (dev)

---

## مراحل Deploy

### 1️⃣ Railway Setup
```bash
# Create account
https://railway.app

# Connect GitHub
# Authorize Railway
```

### 2️⃣ Add Services
```bash
# Create PostgreSQL
Dashboard → + Add Service → PostgreSQL

# Add Web Service
Dashboard → + New Project → GitHub Repo
Branch: railway-deployment
```

### 3️⃣ Configuration
```bash
Build:  cd university_site && bash build.sh
Start:  cd university_site && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
Root:   university_site/
```

### 4️⃣ Environment Variables
```
SECRET_KEY          [random secret]
DEBUG               False
ALLOWED_HOSTS       your-app.railway.app
DATABASE_URL        [from PostgreSQL]
EMAIL_HOST_USER     your-email@gmail.com
EMAIL_HOST_PASSWORD [app password]
```

### 5️⃣ Deploy & Migrate
```bash
# Auto-deploy on push

# Then run:
railway run python manage.py migrate
railway run python manage.py createsuperuser
railway run python manage.py collectstatic --noinput
```

### 6️⃣ Verify
```
https://your-app.railway.app
https://your-app.railway.app/admin/
```

---

## Troubleshooting

### 500 Error
```bash
# Check logs
railway logs

# Common issues:
# - SECRET_KEY not set
# - DATABASE_URL wrong
# - Missing migration
```

### Static Files 404
```bash
railway run python manage.py collectstatic --noinput
```

### Database Connection
```bash
# Verify DATABASE_URL
echo $DATABASE_URL

# Should be: postgresql://user:pass@host:port/db
```

### Email Not Sending
```
✅ 2FA enabled in Gmail
✅ Using App Password (not main password)
✅ Correct EMAIL_HOST_USER and PASSWORD
```

---

## ✅ Checklist

- [ ] Branch `railway-deployment` created
- [ ] All files committed
- [ ] Railway account created
- [ ] PostgreSQL added
- [ ] Web Service configured
- [ ] Environment variables set
- [ ] Deployed successfully
- [ ] Migrations ran
- [ ] Superuser created
- [ ] Site verified
- [ ] Admin accessible
- [ ] Emails configured

---

## 📚 Resources

- [Railway Documentation](https://docs.railway.app)
- [Django + Railway Guide](https://docs.railway.app/guides/django)
- [PostgreSQL on Railway](https://docs.railway.app/databases/postgresql)
- [Railway CLI](https://docs.railway.app/developers/cli)

---

## 🚀 You're Ready!

Hamster تمام تنظیمات انجام شده است.

فقط روی Railway لاگین کنید و deploy کنید!

**Happy Deploying! 🎉**
