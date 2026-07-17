# راهنمای دیپلوی پروژه دانشگاه روی cPanel

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

## مراحل دیپلوی

### مرحله ۱: آماده‌سازی پروژه محلی

1. **حذف فایل‌های غیرضروری:**
   - حذف پوشه `venv` (محیط مجازی محلی)
   - حذف پوشه `__pycache__` در تمام اپ‌ها
   - حذف فایل `db.sqlite3` (دیتابیس محلی)

2. **کمپرس کردن پروژه:**
   ```bash
   # در مسیر پروژه
   cd "c:\Users\Part Laptop\Desktop\windows work\uinvercity - Copy (2)"
   # فایل‌های غیرضروری را حذف کنید
   # سپس پروژه را zip کنید
   ```

---

### مرحله ۲: تنظیم دامنه

1. **ورود به پنل NIC:**
   - به آدرس https://new.nic.ir/panel/auth/sign-in وارد شوید
   - با نام کاربری `ab128-irnic` و رمز `@amini1012` وارد شوید

2. **تنظیم DNS:**
   - به بخش مدیریت DNS بروید
   - رکوردهای زیر را اضافه کنید:
     ```
     Type: A Record
     Name: @
     Value: [IP سرور cPanel]
     TTL: 3600
     
     Type: CNAME
     Name: www
     Value: @
     TTL: 3600
     ```

3. **دریافت IP سرور:**
   - وارد cPanel شوید
   - در سمت راست، IP سرور را پیدا کنید
   - این IP را در رکورد A استفاده کنید

---

### مرحله ۳: آپلود پروژه به cPanel

1. **ورود به cPanel:**
   - به آدرس https://p135.talahost.com:2083/ وارد شوید
   - با نام کاربری `cp29524` و رمز `A@mini10121024` وارد شوید

2. **آپلود فایل‌ها:**
   - به بخش **File Manager** بروید
   - به پوشه `public_html` بروید
   - تمام فایل‌های پروژه را آپلود کنید
   - فایل‌های زیر باید در ریشه `public_html` باشند:
     - `manage.py`
     - `passenger_wsgi.py`
     - `.htaccess`
     - پوشه `config/`
     - پوشه `core/`
     - پوشه `accounts/`
     - پوشه `news/`
     - پوشه `academics/`
     - پوشه `faculty/`
     - پوشه `research/`
     - پوشه `library/`
     - پوشه `admissions/`
     - پوشه `contact/`
     - پوشه `dashboard/`
     - پوشه `static/`
     - پوشه `templates/`
     - فایل `requirements.txt`

---

### مرحله ۴: تنظیم محیط Python در cPanel

1. **ایجاد محیط مجازی Python:**
   - در cPanel به بخش **Setup Python App** بروید
   - روی **Create Application** کلیک کنید
   - تنظیمات زیر را وارد کنید:
     ```
     Python version: 3.11
     Application root: university_site
     Application URL: /
     Application startup file: passenger_wsgi.py
     Application entry point: application
     ```
   - روی **Create** کلیک کنید

2. **نصب کتابخانه‌ها:**
   - در بخش **Setup Python App**، روی برنامه ایجاد شده کلیک کنید
   - به بخش **Run pip install** بروید
   - دستور زیر را اجرا کنید:
     ```
     pip install -r requirements.txt
     ```

---

### مرحله ۵: تنظیم دیتابیس MySQL

1. **ایجاد دیتابیس:**
   - در cPanel به بخش **MySQL Database Wizard** بروید
   - نام دیتابیس: `cp29524_university`
   - نام کاربری: `cp29524_univuser`
   - رمز عبور: [یک رمز قوی انتخاب کنید]
   - دسترسی کامل (ALL PRIVILEGES) بدهید

2. **به‌روزرسانی settings_production.py:**
   - در File Manager، فایل `config/settings_production.py` را ویرایش کنید
   - اطلاعات دیتابیس را وارد کنید:
     ```python
     DATABASES = {
         'default': {
             'ENGINE': 'django.db.backends.mysql',
             'NAME': 'cp29524_university',
             'USER': 'cp29524_univuser',
             'PASSWORD': 'رمزی_که_انتخاب_کردید',
             'HOST': 'localhost',
             'PORT': '3306',
         }
     }
     ```

3. **تغییر SECRET_KEY:**
   - یک SECRET_KEY جدید تولید کنید:
     ```python
     python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
     ```
   - در `settings_production.py` جایگزین کنید

---

### مرحله ۶: اجرای Migrationها

1. **ایجاد پوشه logs:**
   - در File Manager، پوشه `logs` در ریشه پروژه ایجاد کنید

2. **اجرای دستورات Django:**
   - در بخش **Setup Python App**، روی **Run Console** کلیک کنید
   - دستورات زیر را اجرا کنید:
     ```bash
     python manage.py migrate --settings=config.settings_production
     python manage.py collectstatic --settings=config.settings_production --noinput
     python manage.py createsuperuser --settings=config.settings_production
     ```

3. **ایجاد ادمین:**
   - نام کاربری: `admin`
   - ایمیل: ایمیل شما
   - رمز عبور: یک رمز قوی

---

### مرحله ۷: تنظیم فایل‌های Static و Media

1. **ایجاد پوشه‌ها:**
   - در File Manager، پوشه‌های زیر را در `public_html` ایجاد کنید:
     - `public/static`
     - `public/media`

2. **تنظیم مجوزها:**
   - روی پوشه `media` کلیک راست کنید
   - **Change Permissions** را انتخاب کنید
   - مجوز را روی `755` تنظیم کنید

---

### مرحله ۸: تنظیم Passenger

1. **ویرایش passenger_wsgi.py:**
   - مسیر Python را بررسی کنید و در صورت نیاز اصلاح کنید
   - مسیر معمولاً در cPanel نمایش داده می‌شود

2. **ویرایش .htaccess:**
   - مسیرها را مطمئن شوید درست هستند
   - اگر SSL نصب شد، بخش redirect HTTPS را فعال کنید

---

### مرحله ۹: راه‌اندازی مجدد

1. **Restart Application:**
   - در بخش **Setup Python App**، روی **Restart** کلیک کنید

2. **بررسی لاگ‌ها:**
   - به بخش **Error Logs** در cPanel بروید
   - اگر خطایی وجود دارد، بررسی کنید

---

### مرحله ۱۰: تست نهایی

1. **ورود به سایت:**
   - آدرس دامنه خود را باز کنید
   - بررسی کنید که سایت درست بارگذاری می‌شود

2. **ورود به پنل ادمین:**
   - به `/admin/` بروید
   - با ادمین ایجاد شده وارد شوید
   - بررسی کنید که پنل کار می‌کند

3. **بررسی فایل‌های Static:**
   - مطمئن شوید CSS و JS درست بارگذاری می‌شوند
   - اگر نه، دستور collectstatic را دوباره اجرا کنید

---

## عیب‌یابی

### خطای 500 Internal Server Error

1. **بررسی لاگ‌ها:**
   - به `public_html/logs/django.log` بروید
   - خطا را بررسی کنید

2. **مشکلات رایج:**
   - مسیرهای غلط در `passenger_wsgi.py`
   - کتابخانه‌های نصب نشده
   - تنظیمات دیتابیس غلط

### فایل‌های Static بارگذاری نمی‌شوند

1. **اجرای مجدد collectstatic:**
   ```bash
   python manage.py collectstatic --settings=config.settings_production --noinput
   ```

2. **بررسی مجوزها:**
   - مطمئن شوید پوشه `public/static` مجوز `755` دارد

### خطای دیتابیس

1. **بررسی اتصال:**
   - در Console، دستور زیر را اجرا کنید:
     ```bash
     python manage.py dbshell --settings=config.settings_production
     ```

2. **بررسی کاراکتر ست:**
   - مطمئن شوید دیتابیس UTF-8 است

---

## امنیت

### پس از دیپلوی موفق:

1. **فعال کردن HTTPS:**
   - در cPanel، SSL رایگان (Let's Encrypt) نصب کنید
   - در `settings_production.py`، تنظیمات زیر را فعال کنید:
     ```python
     SECURE_SSL_REDIRECT = True
     SESSION_COOKIE_SECURE = True
     CSRF_COOKIE_SECURE = True
     ```

2. **حذف فایل‌های حساس:**
   - مطمئن شوید `db.sqlite3` محلی آپلود نشده است
   - فایل `.git` را اگر وجود دارد حذف کنید

3. **تنظیم ALLOWED_HOSTS:**
   - در `settings_production.py`:
     ```python
     ALLOWED_HOSTS = ['yourdomain.com', 'www.yourdomain.com']
     ```

---

## پشتیبانی

در صورت بروز مشکل:
1. لاگ‌های Django را بررسی کنید: `logs/django.log`
2. لاگ‌های Apache را در cPanel بررسی کنید
3. از بخش **Setup Python App**، لاگ‌های Passenger را بررسی کنید

---

## نکات مهم

- **پشتیبان‌گیری:** قبل از هر تغییری از دیتابیس بکاپ بگیرید
- **به‌روزرسانی:** کتابخانه‌ها را به‌صورت دوره‌ای به‌روزرسانی کنید
- **نظارت:** لاگ‌ها را مرتب بررسی کنید
- **امنیت:** رمزهای قوی استفاده کنید و آنها را مرتب تغییر دهید
