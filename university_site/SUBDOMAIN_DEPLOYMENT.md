# راهنمای دیپلوی پروژه دانشگاه روی Subdomain

## هدف
دیپلوی پروژه دانشگاه روی subdomain جداگانه برای جلوگیری از تداخل با پروژه قبلی

---

## اطلاعات دسترسی

### cPanel
- **آدرس:** https://p135.talahost.com:2083/
- **نام کاربری:** cp29524
- **رمز:** A@mini10121024

### پنل دامنه (NIC)
- **آدرس:** https://new.nic.ir/panel/auth/sign-in
- **نام کاربری:** ab128-irnic
- **رمز:** @amini1012

---

## ساختار نهایی

```
public_html/
├── project1/              # پروژه قبلی (تغییر نمی‌کند)
│   └── ...
└── university/            # پروژه دانشگاه (جدید)
    ├── manage.py
    ├── passenger_wsgi.py
    ├── .htaccess
    ├── config/
    ├── core/
    ├── accounts/
    ├── news/
    ├── academics/
    ├── faculty/
    ├── research/
    ├── library/
    ├── admissions/
    ├── contact/
    ├── dashboard/
    ├── static/
    ├── templates/
    ├── media/
    ├── logs/
    └── requirements.txt
```

---

## مراحل دیپلوی

### مرحله ۱: آماده‌سازی پروژه محلی

```bash
# 1. حذف فایل‌های غیرضروری
cd "c:\Users\Part Laptop\Desktop\windows work\uinvercity - Copy (2)\university_site"
rm -rf venv
rm -rf __pycache__
rm db.sqlite3
find . -type d -name __pycache__ -exec rm -rf {} +

# 2. کمپرس کردن پروژه
# پوشه university_site را zip کنید
```

---

### مرحله ۲: ایجاد Subdomain در cPanel

1. **ورود به cPanel:**
   - به آدرس https://p135.talahost.com:2083/ وارد شوید
   - با نام کاربری `cp29524` و رمز `A@mini10121024` وارد شوید

2. **ایجاد Subdomain:**
   - به بخش **Domains** → **Subdomains** بروید
   - تنظیمات زیر را وارد کنید:
     ```
     Subdomain: university
     Domain: [دامنه اصلی شما]
     Document Root: public_html/university
     ```
   - روی **Create** کلیک کنید

3. **نتیجه:**
   - پروژه قبلی: `yourdomain.com`
   - پروژه دانشگاه: `university.yourdomain.com`

---

### مرحله ۳: آپلود پروژه

1. **ورود به File Manager:**
   - در cPanel به **File Manager** بروید
   - به پوشه `public_html/university` بروید

2. **آپلود فایل‌ها:**
   - فایل zip پروژه را آپلود کنید
   - Extract کنید
   - مطمئن شوید ساختار درست است

---

### مرحله ۴: ایجاد دیتابیس جداگانه

1. **به MySQL Database Wizard بروید:**
   - در cPanel به **Databases** → **MySQL Database Wizard** بروید

2. **Step 1 - Create Database:**
   - نام دیتابیس: `cp29524_university_db`
   - روی **Next Step** کلیک کنید

3. **Step 2 - Create Database User:**
   - نام کاربری: `cp29524_univ_user`
   - رمز عبور: [یک رمز قوی انتخاب کنید]
   - روی **Create User** کلیک کنید

4. **Step 3 - Add User to Database:**
   - **ALL PRIVILEGES** را انتخاب کنید
   - روی **Make Changes** کلیک کنید

5. **یادداشت اطلاعات:**
   ```
   Database: cp29524_university_db
   User: cp29524_univ_user
   Password: [رمزی که انتخاب کردید]
   ```

---

### مرحله ۵: تنظیمات Production

1. **ویرایش settings_production.py:**
   - در File Manager، فایل `config/settings_production.py` را ویرایش کنید
   - اطلاعات دیتابیس را وارد کنید:
     ```python
     DATABASES = {
         'default': {
             'ENGINE': 'django.db.backends.mysql',
             'NAME': 'cp29524_university_db',
             'USER': 'cp29524_univ_user',
             'PASSWORD': 'رمزی_که_انتخاب_کردید',
             'HOST': 'localhost',
             'PORT': '3306',
         }
     }
     ```

2. **تولید SECRET_KEY جدید:**
   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```
   - در `settings_production.py` جایگزین کنید:
     ```python
     SECRET_KEY = 'کلید_جدید_تولید_شده'
     ```

3. **تنظیم ALLOWED_HOSTS:**
   ```python
   ALLOWED_HOSTS = ['university.yourdomain.com', 'www.university.yourdomain.com']
   ```

---

### مرحله ۶: تنظیم محیط Python

1. **ایجاد Python Application:**
   - در cPanel به **Software** → **Setup Python App** بروید
   - روی **Create Application** کلیک کنید
   - تنظیمات زیر را وارد کنید:
     ```
     Python version: 3.11
     Application root: university
     Application URL: /university
     Application startup file: passenger_wsgi.py
     Application entry point: application
     Passenger log file: logs/passenger.log
     ```
   - روی **Create** کلیک کنید

2. **نصب کتابخانه‌ها:**
   - روی برنامه ایجاد شده کلیک کنید
   - به بخش **Run pip install** بروید
   - دستور زیر را اجرا کنید:
     ```bash
     pip install -r requirements.txt
     ```

3. **صبر کنید تا نصب کامل شود**
   - ممکن است ۵-۱۰ دقیقه طول بکشد

---

### مرحله ۷: ایجاد پوشه‌های مورد نیاز

1. **در File Manager:**
   - پوشه `logs` در `public_html/university` ایجاد کنید
   - پوشه `public/static` در `public_html/university` ایجاد کنید
   - پوشه `public/media` در `public_html/university` ایجاد کنید

2. **تنظیم مجوزها:**
   - روی پوشه `media` کلیک راست کنید
   - **Change Permissions** → `755`

---

### مرحله ۸: اجرای Migrationها

1. **باز کردن Console:**
   - در **Setup Python App**، روی **Run Console** کلیک کنید

2. **اجرای دستورات:**
   ```bash
   cd /home/cp29524/public_html/university
   python manage.py migrate --settings=config.settings_production
   python manage.py collectstatic --settings=config.settings_production --noinput
   python manage.py createsuperuser --settings=config.settings_production
   ```

3. **ایجاد ادمین:**
   - نام کاربری: `admin`
   - ایمیل: ایمیل شما
   - رمز عبور: یک رمز قوی

---

### مرحله ۹: راه‌اندازی مجدد

1. **Restart Application:**
   - در **Setup Python App**، روی **Restart** کلیک کنید

2. **بررسی وضعیت:**
   - مطمئن شوید وضعیت **Running** است

---

### مرحله ۱۰: تست نهایی

1. **باز کردن سایت:**
   - آدرس: `http://university.yourdomain.com`
   - بررسی کنید که سایت درست بارگذاری می‌شود

2. **تست پنل ادمین:**
   - آدرس: `http://university.yourdomain.com/admin/`
   - با ادمین ایجاد شده وارد شوید

3. **تست فایل‌های Static:**
   - بررسی کنید که CSS و JS درست بارگذاری می‌شوند

---

## تنظیم DNS (اختیاری)

اگر subdomain کار نمی‌کند:

1. **ورود به پنل NIC:**
   - به آدرس https://new.nic.ir/panel/auth/sign-in وارد شوید
   - با نام کاربری `ab128-irnic` و رمز `@amini1012` وارد شوید

2. **اضافه کردن رکورد CNAME:**
   ```
   Type: CNAME
   Name: university
   Value: @
   TTL: 3600
   ```

3. **صبر کنید:**
   - ممکن است ۱-۲ ساعت طول بکشد تا DNS propagate شود

---

## فعال کردن HTTPS (پس از دیپلوی موفق)

1. **نصب SSL:**
   - در cPanel به **Security** → **SSL/TLS Status** بروید
   - روی `university.yourdomain.com` کلیک کنید
   - روی **Run AutoSSL** کلیک کنید

2. **فعال کردن Redirect:**
   - در `config/settings_production.py`:
     ```python
     SECURE_SSL_REDIRECT = True
     SESSION_COOKIE_SECURE = True
     CSRF_COOKIE_SECURE = True
     ```

3. **فعال کردن در .htaccess:**
   - خطوط redirect HTTPS را از حالت comment خارج کنید

4. **Restart Application**

---

## عیب‌یابی

### خطای 500 Internal Server Error

1. **بررسی لاگ‌ها:**
   - `public_html/university/logs/django.log`
   - `public_html/university/logs/passenger.log`

2. **مشکلات رایج:**
   - مسیر غلط در `passenger_wsgi.py`
   - کتابخانه‌های نصب نشده
   - تنظیمات دیتابیس غلط

### فایل‌های Static بارگذاری نمی‌شوند

```bash
python manage.py collectstatic --settings=config.settings_production --noinput
```

### خطای دیتابیس

```bash
python manage.py dbshell --settings=config.settings_production
```

---

## چک‌لیست نهایی

- [ ] Subdomain ایجاد شده
- [ ] پروژه در پوشه `public_html/university` آپلود شده
- [ ] دیتابیس `cp29524_university_db` ایجاد شده
- [ ] کاربر `cp29524_univ_user` ایجاد شده
- [ ] settings_production.py به‌روزرسانی شده
- [ ] SECRET_KEY جدید تولید شده
- [ ] ALLOWED_HOSTS تنظیم شده
- [ ] Python Application ایجاد شده
- [ ] کتابخانه‌ها نصب شده
- [ ] Migrationها اجرا شده
- [ ] collectstatic اجرا شده
- [ ] Superuser ایجاد شده
- [ ] Application Restart شده
- [ ] سایت تست شده
- [ ] پنل ادمین تست شده

---

## نتیجه

پروژه دانشگاه روی `university.yourdomain.com` اجرا می‌شود و کاملاً از پروژه قبلی جدا است.
