# 🚀 راهنمای کامل Deploy روی Railway - قدم به قدم

## 📋 فهرست مطالب
1. [آماده‌سازی Railway Account](#1-آماده‌سازی-railway-account)
2. [اتصال GitHub](#2-اتصال-github)
3. [ایجاد PostgreSQL Database](#3-ایجاد-postgresql-database)
4. [ایجاد Railway Service](#4-ایجاد-railway-service)
5. [تنظیم Environment Variables](#5-تنظیم-environment-variables)
6. [اجرای Migrations](#6-اجرای-migrations)
7. [Testing و Troubleshooting](#7-testing-و-troubleshooting)

---

## 1. آماده‌سازی Railway Account

### مرحله 1.1: ثبت‌نام و لاگین
1. برو به https://railway.app
2. **Sign Up** کنید (یا لاگین کنید)
3. از **GitHub** استفاده کنید (توصیه می‌شود)
4. **GitHub Authorize** کنید

### مرحله 1.2: پروفایل و Billing
1. بعد از لاگین، روی **Dashboard** برو
2. **Account** → **Billing** (اختیاری - یک کریڈیت کارت برای paid services)
3. برای شروع، فقط **Free Tier** کافی است

---

## 2. اتصال GitHub

### مرحله 2.1: نمایش Repository
1. **Dashboard** → **New Project**
2. یا **Projects** → **+ New Project**

### مرحله 2.2: انتخاب Repository
1. **GitHub** را انتخاب کنید
2. اگر اولین بار است، **Authorize Railway** کلیک کنید
3. `Davoadeivai/university-site` repository را جستجو و انتخاب کنید
4. **Deploy** کلیک کنید

---

## 3. ایجاد PostgreSQL Database

### مرحله 3.1: افزودن Database
1. **Dashboard** → **Project**
2. **+ Add Service** → **Database** → **PostgreSQL**

### مرحله 3.2: تنظیمات
Railway خودکار تنظیمات را انجام می‌دهد:
- **Name:** `university-db`
- **Username:** `postgres`
- **Database:** `railway` (یا همان اسم project)
- **Port:** `5432`

### مرحله 3.3: نوت کردن CONNECTION STRING
1. **PostgreSQL** service را انتخاب کنید
2. **Variables** تب کلیک کنید
3. **DATABASE_URL** را کپی کنید
4. این رشته را برای بعد **ذخیره** کنید

```
مثال:
postgresql://postgres:xxxxx@containers-us-west-xxx.railway.app:7654/railway
```

---

## 4. ایجاد Railway Service

### مرحله 4.1: فیلم بخش Web
1. اگر هنوز service ایجاد نشده، **+ Add Service** کلیک کنید
2. **GitHub Repo** را انتخاب کنید
3. `university-site` انتخاب کنید

### مرحله 4.2: تنظیمات GitHub
Railway خودکار تشخیص می‌دهد:
- **Branch:** `railway-deployment`
- **Root Directory:** `university_site/`

### مرحله 4.3: Build & Deploy Configuration
1. **Settings** تب کلیک کنید
2. **Build Command:**
```bash
cd university_site && bash build.sh
```
3. **Start Command:**
```bash
cd university_site && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
```

### مرحله 4.4: Deploy
- **Deploy** کلیک کنید
- منتظر بمانید (اولین deploy ۳-۵ دقیقه طول می‌کشد)

---

## 5. تنظیم Environment Variables

### مرحله 5.1: باز کردن Environment Variables
1. **Web Service** → **Variables** تب

### مرحله 5.2: اضافه کردن متغیرها

**یکی یکی این متغیرها ر�� اضافه کنید:**

#### 5.2.1 SECRET_KEY
```
Key:   SECRET_KEY
Value: (از دجکرتی یا دستور زیر)
```

برای تولید:
```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

**مثال:**
```
django-insecure-v!@_^s&-c$%^&*()_+=-][}]{";
```

#### 5.2.2 DEBUG
```
Key:   DEBUG
Value: False
```

#### 5.2.3 ALLOWED_HOSTS
```
Key:   ALLOWED_HOSTS
Value: your-app-name.railway.app
```

> ℹ️ نام app: روی **Deployments** → **Railway URL** ببینید
> مثال: `university-site-production.railway.app`

#### 5.2.4 DATABASE_URL
```
Key:   DATABASE_URL
Value: (رشته‌ای که از PostgreSQL کپی کردید)
```

**مثال:**
```
postgresql://postgres:xxxxx@containers-us-west-xxx.railway.app:7654/railway
```

#### 5.2.5 EMAIL_HOST_USER
```
Key:   EMAIL_HOST_USER
Value: your-email@gmail.com
```

#### 5.2.6 EMAIL_HOST_PASSWORD
```
Key:   EMAIL_HOST_PASSWORD
Value: XXXX XXXX XXXX XXXX
```

> 🔐 **نحوه دریافت Google App Password:**
> 1. برو به https://myaccount.google.com/apppasswords
> 2. 2FA را فعال کنید (اگر نشده)
> 3. **Mail** و **Windows Computer** انتخاب کنید
> 4. **Generate** کلیک کنید
> 5. 16 کاراکتر password را کپی کنید

### مرحله 5.3: ذخیره و Redeploy
- بعد از اضافه کردن variables، **Redeploy** کلیک کنید
- یا خودکار تغییرات deploy می‌شود

---

## 6. اجرای Migrations

### مرحله 6.1: اتصال به Shell
1. **Web Service** → **Deployments**
2. آخرین deployment را انتخاب کنید
3. **View Logs** یا **Open Shell**

### مرحله 6.2: Database Migrations
```bash
cd university_site
python manage.py migrate
```

✅ باید ببینید:
```
Operations to perform:
  Apply all migrations: ...
Running migrations:
  Applying ... OK
```

### مرحله 6.3: ایجاد Superuser
```bash
python manage.py createsuperuser
```

وقتی prompt ظاهر شد:
```
Username: admin
Email: your-email@gmail.com
Password: (رمز قوی)
Password (again): (دوباره)
```

### مرحله 6.4: Collect Static (اختیاری)
```bash
python manage.py collectstatic --noinput
```

---

## 7. Testing و Troubleshooting

### مرحله 7.1: بررسی سایت
```
https://your-app-name.railway.app
```

✅ اگر صفحه اصلی نمایش داده شد: **Deploy موفق!** 🎉

### مرحله 7.2: بررسی Admin
```
https://your-app-name.railway.app/admin/
```

لاگین:
- Username: `admin`
- Password: (رمزی که وارد کردید)

### مرحله 7.3: حل مشکلات

#### ❌ **500 Error**
```bash
# Logs را بررسی کنید
# Deployments → View Logs
```

خطاهای معمول:
- `SECRET_KEY not found` → تنظیم کنید
- `DATABASE_URL` → چک کنید درست است
- `DEBUG=True` موقتاً برای دیدن جزئیات

#### ❌ **Static Files 404**
```bash
cd university_site
python manage.py collectstatic --noinput
```

#### ❌ **Database Connection Error**
```bash
# DATABASE_URL را چک کنید
echo $DATABASE_URL
```

#### ❌ **Cannot find module**
```bash
pip install -r requirements.txt
```

#### ❌ **Email نمی‌رسد**
- 2FA در Gmail فعال است؟
- App Password استفاده می‌کنید (نه اصلی)؟
- EMAIL_HOST_USER درست است؟

---

## ✅ Checklist - بعد از Deploy

- [ ] سایت در `https://your-app.railway.app` باز می‌شود
- [ ] Admin panel دسترسی پذیر است
- [ ] می‌توانید login کنید
- [ ] Static files نمایش داده می‌شوند
- [ ] تماس فرم کار می‌کند
- [ ] Email ارسال می‌شود (اختیاری)
- [ ] تمام صفحات لود می‌شوند

---

## 📱 Railway CLI (اختیاری)

### نصب
```bash
npm i -g @railway/cli
```

### لاگین
```bash
railway login
```

### Migration از Command Line
```bash
railway run python manage.py migrate
```

### Logs
```bash
railway logs
```

---

## 🔐 نکات ایمنی

⚠️ **مهم:**
1. `SECRET_KEY` را هرگز commit نکنید
2. `DEBUG=False` در Production
3. Railway خودکار HTTPS فعال می‌کند
4. `ALLOWED_HOSTS` را دقیق تنظیم کنید
5. App Passwords برای Email
6. Database backups قبل از production

---

## 📚 منابع

- **Railway Docs:** https://docs.railway.app
- **Django + Railway:** https://docs.railway.app/guides/django
- **PostgreSQL:** https://docs.railway.app/databases/postgresql
- **Environment Variables:** https://docs.railway.app/develop/variables

---

## 🎯 خلاصه

```
1. Railway Account
    ↓
2. GitHub Connection
    ↓
3. PostgreSQL Database
    ↓
4. Web Service
    ↓
5. Environment Variables
    ↓
6. Deploy (خودکار)
    ↓
7. Migrations
    ↓
8. Create Superuser
    ↓
9. ✅ Live!
```

---

**سوالی داشتید؟ Railway Support منو کمک کنید!** 🚀
