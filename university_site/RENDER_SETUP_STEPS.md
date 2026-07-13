# 🚀 راهنمای کامل Deploy روی Render - قدم به قدم

## 📋 فهرست مطالب
1. [آماده‌سازی Render Account](#1-آماده‌سازی-render-account)
2. [ایجاد PostgreSQL Database](#2-ایجاد-postgresql-database)
3. [ایجاد Web Service](#3-ایجاد-web-service)
4. [تنظیم Environment Variables](#4-تنظیم-environment-variables)
5. [اجرای Migrations](#5-اجرای-migrations)
6. [Testing و Troubleshooting](#6-testing-و-troubleshooting)

---

## 1. آماده‌سازی Render Account

### مرحله 1.1: ثبت‌نام و لاگین
1. برو به https://render.com
2. **Sign Up** کنید (یا لاگین کنید)
3. از **GitHub** استفاده کنید (توصیه می‌شود)

### مرحله 1.2: اتصال GitHub
1. روی **Dashboard** کلیک کنید
2. **Settings** → **Connections** → **GitHub**
3. **Connect Repository** را انتخاب کنید
4. `Davoadeivai/university-site` repository را پیدا و انتخاب کنید
5. **Authorize** کنید

---

## 2. ایجاد PostgreSQL Database

### مرحله 2.1: ایجاد Database
1. در Render Dashboard، روی **New +** کلیک کنید
2. **PostgreSQL** را انتخاب کنید

### مرحله 2.2: تنظیمات Database
```
Name:              university-db
Database:          university_db
Username:          postgres
Region:            (خودتان انتخاب کنید - نزدیک‌تر بهتر)
PostgreSQL Version: (آخرین نسخه)
Plan:              Free (شروع با رایگان)
```

### مرحله 2.3: نوت کردن CONNECTION STRING
- بعد از ایجاد، Render یک **CONNECTION STRING** نشان می‌دهد
- این رشته را **کجی کنید** - به زودی نیاز داریم
- فرمت: `postgresql://user:password@host:5432/database`

```
مثال:
postgresql://postgres:your_random_password@dpg-xxxx.render.com:5432/university_db
```

---

## 3. ایجاد Web Service

### مرحله 3.1: ایجاد Service
1. **Dashboard** → **New +** → **Web Service**

### مرحله 3.2: انتخاب Repository
1. برای **GitHub** اتصال؟ → **Yes**
2. Repository: `Davoadeivai/university-site`
3. **Search** کنید و انتخاب کنید

### مرحله 3.3: تنظیمات اولیه
```
Name:               university-site
Runtime:            Python 3
Build Command:      cd university_site && bash build.sh
Start Command:      cd university_site && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
Branch:             render-deployment
Region:             (همان منطقه Database)
Plan:               Free (شروع کنید)
```

### مرحله 3.4: ایجاد Service
- **Create Web Service** کلیک کنید
- منتظر بمانید (اولین build ممکن است ۳-۵ دقیقه طول بکشد)

---

## 4. تنظیم Environment Variables

### مرحله 4.1: باز کردن Environment Variables
1. **Service Dashboard** → **Environment**
2. یا **Settings** → **Environment**

### مرحله 4.2: اضافه کردن متغیرها

**یکی یکی این متغیرها را اضافه کنید:**

#### 4.2.1 SECRET_KEY
```
Key:   SECRET_KEY
Value: (از زیر کپی کنید و paste کنید)
```

برای تولید SECRET_KEY، یکی از این گزینه‌ها:
- **آنلاین:** https://djecrety.ir/
- **یا محلی:**
```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

**مثال:**
```
django-insecure-v!@_^s&-c$%^&*()_+=-][}]{";':".,<>?/\|`~!@#$%
```

#### 4.2.2 DEBUG
```
Key:   DEBUG
Value: False
```

#### 4.2.3 ALLOWED_HOSTS
```
Key:   ALLOWED_HOSTS
Value: your-app-name.onrender.com
```

> ⚠️ جای `your-app-name` را با نام واقعی service بگذارید
> مثال اگر name: `university-site` باشد:
> ```
> ALLOWED_HOSTS = university-site.onrender.com
> ```

#### 4.2.4 DATABASE_URL
```
Key:   DATABASE_URL
Value: postgresql://postgres:PASSWORD@HOST:5432/DBNAME
```

> ✅ این رشته‌ای است که از PostgreSQL کپی کردید
> مثال:
> ```
> postgresql://postgres:abc123xyz@dpg-xxxx.render.com:5432/university_db
> ```

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
> 2. اگر 2FA فعال نیست، اول آن را فعال کنید
> 3. Select: **Mail** و **Windows Computer** (یا دستگاه خود)
> 4. **Generate** کلیک کنید
> 5. Password 16 کاراکتری را کپی کنید (بدون space)
> 6. Paste کنید

### مرحله 4.3: ذخیره کردن
- **Save** کلیک کنید
- Service خودکار **restart** می‌شود

---

## 5. اجرای Migrations

بعد از اینکه Environment Variables تنظیم شدند و Service با موفقیت **deployed** شد:

### مرحله 5.1: اتصال به Shell Render
1. **Dashboard** → Service → **Shell**
2. یا از Render CLI (اگر نصب کرده باشید)

### مرحله 5.2: Database Migrations
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
  Applying ... OK
```

### مرحله 5.3: ایجاد Superuser (Admin)
```bash
python manage.py createsuperuser
```

وقتی prompt ظاهر شد:
```
Username: admin
Email: your-email@gmail.com
Password: (یک رمز قوی وارد کنید)
Password (again): (دوباره تایپ کنید)
```

### مرحله 5.4: جمع‌آوری Static Files (اختیاری)
```bash
python manage.py collectstatic --noinput
```

---

## 6. Testing و Troubleshooting

### مرحله 6.1: بررسی سایت
```
https://your-app-name.onrender.com
```

✅ اگر صفحه اصلی نمایش داده شد: **تبریک! Deploy موفق بود!** 🎉

### مرحله 6.2: بررسی Admin Panel
```
https://your-app-name.onrender.com/admin/
```

وارد شوید با:
- Username: `admin`
- Password: (رمزی که وارد کردید)

### مرحله 6.3: حل مشکلات

#### ❌ **500 Error**
```bash
# Logs را بررسی کنید:
# Dashboard → Logs
```

اگر ERROR دیدید:
- `SECRET_KEY not found` → چک کنید SECRET_KEY تنظیم شده
- `DATABASE_URL` → چک کنید DATABASE_URL درست است
- `DEBUG=True` موقتاً برای دیدن خطا

#### ❌ **Static Files نمایش داده نمی‌شود (404)**
```bash
cd university_site
python manage.py collectstatic --noinput
```

#### ❌ **Cannot connect to database**
```bash
# Database credentials را چک کنید
# postgresql://USERNAME:PASSWORD@HOST:5432/DATABASE
```

#### ❌ **Email نمی‌رسد**
- چک کنید 2FA در Gmail فعال است
- چک کنید از **App Password** استفاده می‌کنید (نه رمز اصلی)
- در Gmail، دنبال "Less secure app" یا "Allow less secure apps" نگردید - نیازی نیست

#### ❌ **Build Failed**
```bash
# Logs را بررسی کنید
# Build Command را اجرا کنید محلی:
cd university_site
bash build.sh
python manage.py migrate
python manage.py runserver
```

---

## ✅ Checklist - بعد از Deploy

- [ ] سایت در `https://your-app-name.onrender.com` باز می‌شود
- [ ] Admin panel در `/admin/` دسترسی پذیر است
- [ ] می‌توانید login کنید
- [ ] Static files نمایش داده می‌شوند (CSS, JS)
- [ ] تماس فرم کار می‌کند
- [ ] Email ارسال می‌شود (اختیاری - اگر تنظیم کردید)
- [ ] صفحات مختلف لود می‌شوند

---

## 📞 Support و منابع

- **Render Docs:** https://render.com/docs/deploy-django
- **Django Deployment:** https://docs.djangoproject.com/en/5.2/howto/deployment/
- **Whitenoise:** http://whitenoise.evans.io/
- **PostgreSQL on Render:** https://render.com/docs/postgres

---

## 🔐 نکات ایمنی

⚠️ **مهم:**
1. هرگز `SECRET_KEY` را در Repository commit نکنید
2. `DEBUG` را همیشه `False` نگه دارید در Production
3. Render خودکار HTTPS فعال می‌کند
4. `ALLOWED_HOSTS` را دقیق تنظیم کنید (نه `*`)
5. App Passwords را برای Email استفاده کنید

---

## 🎯 خلاصه مراحل

```mermaid
1. Render Account ایجاد
         ↓
2. PostgreSQL Database
         ↓
3. Web Service ایجاد
         ↓
4. Environment Variables
         ↓
5. Deploy (خودکار)
         ↓
6. Database Migrations
         ↓
7. Create Superuser
         ↓
8. ✅ Live!
```

---

**سوالی داشتید؟ منو کال کنید!** 📱
