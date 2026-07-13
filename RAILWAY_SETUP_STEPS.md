# 🚂 راهنمای کامل Deploy روی Railway - قدم به قدم

## 📋 فهرست مطالب
1. [آماده‌سازی Railway Account](#1-آماده‌سازی-railway-account)
2. [ایجاد PostgreSQL Database](#2-ایجاد-postgresql-database)
3. [ایجاد Railway Service](#3-ایجاد-railway-service)
4. [تنظیم Environment Variables](#4-تنظیم-environment-variables)
5. [اجرای Migrations](#5-اجرای-migrations)
6. [Testing و Troubleshooting](#6-testing-و-troubleshooting)

---

## 1. آماده‌سازی Railway Account

### مرحله 1.1: ثبت‌نام و لاگین
1. برو به https://railway.app
2. **Sign Up** کنید (یا لاگین کنید)
3. از **GitHub** استفاده کنید (توصیه می‌شود)
4. **Authorize** Railway برای GitHub

---

## 2. ایجاد PostgreSQL Database

### مرحله 2.1: ایجاد Database
1. در Railway Dashboard، روی **New Project** کلیک کنید
2. **+ Add Service** → **Database** → **PostgreSQL**

### مرحله 2.2: نوت کردن CONNECTION STRING
- بعد از ایجاد، **Variables** tab کلیک کنید
- **DATABASE_URL** را کپی کنید
- این رشته را **ذخیره** کنید - به زودی نیاز داریم

**فرمت:**
```
postgresql://postgres:password@host:port/database
```

---

## 3. ایجاد Railway Service

### مرحله 3.1: اضافه کردن Web Service
1. **+ New Project** → **GitHub Repo**
2. انتخاب کنید: `Davoadeivai/university-site`
3. **Deploy** کلیک کنید

### مرحله 3.2: انتخاب Branch
- Railway خودکار **main** را انتخاب می‌کند
- اگر **railway-fix** را می‌خواهید، تغییر دهید
- **Deploy** کلیک کنید

### مرحله 3.3: تنظیمات Build
1. **Settings** tab کلیک کنید
2. **Build Command:**
```bash
bash build.sh
```
3. **Start Command:**
```bash
gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
```
4. **Save** کلیک کنید

---

## 4. تنظیم Environment Variables

### مرحله 4.1: باز کردن Variables
1. **Web Service** → **Variables** tab

### مرحله 4.2: اضافه کردن هر متغیر

#### 4.2.1 SECRET_KEY
```
Key:   SECRET_KEY
Value: (تولید کنید - زیر را ببینید)
```

**تولید SECRET_KEY:**
```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

**مثال:**
```
django-insecure-v!@_^s&-c$%^&*()
```

#### 4.2.2 DEBUG
```
Key:   DEBUG
Value: False
```

#### 4.2.3 ALLOWED_HOSTS
```
Key:   ALLOWED_HOSTS
Value: your-app-name.railway.app
```

> ℹ️ نام app را از **Deployments URL** بگیرید

#### 4.2.4 DATABASE_URL
```
Key:   DATABASE_URL
Value: (از PostgreSQL service کپی کردید)
```

**مثال:**
```
postgresql://postgres:abc123xyz@dpg-xxxx.railway.app:5432/railway
```

#### 4.2.5 EMAIL_HOST_USER
```
Key:   EMAIL_HOST_USER
Value: your-email@gmail.com
```

#### 4.2.6 EMAIL_HOST_PASSWORD
```
Key:   EMAIL_HOST_PASSWORD
Value: XXXX XXXX XXXX XXXX
```

> 🔐 **نحوه دریافت Google App Password:**
> 1. برو به https://myaccount.google.com/apppasswords
> 2. 2FA را فعال کنید (اگر نشده)
> 3. **Mail** و **Windows Computer** انتخاب کنید
> 4. **Generate** کلیک کنید
> 5. 16 کاراکتر password را کپی کنید (بدون space)

### مرحله 4.3: ذخیره و Deploy
- **Save** کلیک کنید
- Railway **خودکار redeploy** می‌کند

---

## 5. اجرای Migrations

### مرحله 5.1: بعد از Deploy موفق
1. **Deployments** tab کلیک کنید
2. آخرین deployment (سبز) را انتخاب کنید
3. **Console** یا **Shell** دنبال کنید

### مرحله 5.2: Database Migrations
```bash
python manage.py migrate
```

✅ باید ببینید:
```
Operations to perform:
  Apply all migrations: ...
Running migrations:
  Applying ... OK
```

### مرحله 5.3: ایجاد Superuser
```bash
python manage.py createsuperuser
```

**وارد کنید:**
```
Username: admin
Email: your-email@gmail.com
Password: (یک رمز قوی)
Password (again): (دوباره تایپ کنید)
```

### مرحله 5.4: Collect Static (اختیاری)
```bash
python manage.py collectstatic --noinput
```

---

## 6. Testing و Troubleshooting

### مرحله 6.1: بررسی سایت
```
https://your-app-name.railway.app
```

✅ اگر صفحه اصلی نمایش داده شد: **Deploy موفق!** 🎉

### مرحله 6.2: بررسی Admin
```
https://your-app-name.railway.app/admin/
```

لاگین کنید:
- Username: `admin`
- Password: (رمزی که وارد کردید)

### مرحله 6.3: حل مشکلات

#### ❌ **500 Error**
```bash
# Logs را بررسی کنید
# Deployments → Console
```

**خطاهای معمول:**
- `SECRET_KEY not found` → تنظیم کنید
- `DATABASE_URL wrong` → چک کنید
- `DEBUG=True` → موقتاً برای دیدن خطا

#### ❌ **Static Files 404**
```bash
python manage.py collectstatic --noinput
```

#### ❌ **Cannot connect to database**
```bash
echo $DATABASE_URL
# باید صحیح باشد
```

#### ❌ **Email نمی‌رسد**
- 2FA در Gmail فعال است؟
- App Password استفاده می‌کنید؟
- EMAIL_HOST_USER صحیح است؟

---

## ✅ Checklist - بعد از Deploy

- [ ] سایت در `https://your-app.railway.app` باز می‌شود
- [ ] Admin panel در `/admin/` دسترسی پذیر است
- [ ] می‌توانید login کنید
- [ ] Static files نمایش داده می‌شوند
- [ ] تمام صفحات لود می‌شوند

---

**سوالی داشتید؟ منو کال کنید!** 📱
