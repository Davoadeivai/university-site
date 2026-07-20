# راهنمای دیپلوی پروژه دانشگاه روی cPanel

## هشدار امنیتی
رمزهای cPanel و NIC را در این فایل یا گیت ذخیره نکنید.
اگر قبلاً رمز را در چت/فایل گذاشته‌اید، فوراً هر دو رمز را عوض کنید.

## پیش‌نیاز
- دامنه به IP سرور هاست (A Record) اشاره کند
- در cPanel: Setup Python App + MySQL Database

## مسیر پیشنهادی روی سرور
- Application root: `university` (مثلاً `/home/USERNAME/university` یا `public_html/university`)
- Startup file: `passenger_wsgi.py`
- Entry point: `application`
- Python: 3.11 (یا نزدیک‌ترین نسخه موجود)

## فایل‌های ضروری
- `passenger_wsgi.py`
- `.htaccess` (مسیر PassengerPython را بعد از ساخت اپ در cPanel با مسیر واقعی عوض کنید)
- `.env` روی سرور (از `.env.example` کپی؛ هرگز در گیت نگذارید)
- `config/settings_prod.py`

## متغیرهای .env تولید
```
SECRET_KEY=<رشته‌ی تصادفی بلند>
DEBUG=False
ALLOWED_HOSTS=yourdomain.ir,www.yourdomain.ir
CSRF_TRUSTED_ORIGINS=https://yourdomain.ir,https://www.yourdomain.ir
DB_ENGINE=mysql
DB_NAME=cpXXXX_university
DB_USER=cpXXXX_univuser
DB_PASSWORD=<رمز دیتابیس>
DB_HOST=localhost
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
PAYMENT_GATEWAY=mock
```

## مراحل سریع
1. در NIC: رکورد A دامنه → IP سرور cPanel
2. cPanel → MySQL Databases: دیتابیس + کاربر + دسترسی All Privileges
3. cPanel → Setup Python App: ساخت اپ روی دامنه/ساب‌دامین
4. آپلود محتویات `university_site` به Application root (بدون `venv` و `__pycache__`)
5. Terminal در cPanel:
   ```bash
   source ~/virtualenv/<app_name>/<pyver>/bin/activate
   cd ~/university   # یا مسیر واقعی اپ
   pip install -r requirements.txt
   python manage.py migrate
   python manage.py collectstatic --noinput
   python manage.py createsuperuser
   mkdir -p tmp && touch tmp/restart.txt
   ```
6. Setup Python App → Restart
7. SSL (Let's Encrypt) را روی دامنه فعال کنید

## نکته MySQL
پروژه `PyMySQL` دارد؛ در `config/__init__.py` به‌عنوان MySQLdb رجیستر می‌شود.
