# راهنمای دیپلوی — بدون دست زدن به سایت اصلی

## هشدار حیاتی
سایت اصلی علامه امینی روی دامنه اصلی/`public_html` است.
این پروژه را آنجا آپلود نکنید، جایگزین نکنید و فایل‌هایش را ویرایش نکنید.

فقط روی **ساب‌دامین + پوشه خالی جدا + دیتابیس جدا** دیپلوی کنید.
جزئیات: فایل `SUBDOMAIN_DEPLOYMENT.md`

## امنیت
رمز cPanel/NIC را در گیت یا این فایل ننویسید. اگر لو رفته، فوراً عوض کنید.

## مسیر پیشنهادی روی سرور
```
/home/USERNAME/apps/university_site/     ← کد Django (جدا)
/home/USERNAME/public_html/              ← سایت اصلی (دست نزنید)
```
یا Document Root ساب‌دامین مثل:
```
/home/USERNAME/public_html/uni_app/      ← فقط اگر خالی و مخصوص این اپ باشد
```

## Setup Python App
- Application URL: ساب‌دامین جدید
- Application root: پوشه جدا (بالا)
- Startup: `passenger_wsgi.py`
- Entry: `application`
- Python: 3.11 (یا نزدیک‌ترین)

## .env تولید (روی سرور، نه در گیت)
```
SECRET_KEY=<رشته تصادفی>
DEBUG=False
ALLOWED_HOSTS=new.yourdomain.ir
CSRF_TRUSTED_ORIGINS=https://new.yourdomain.ir
DB_ENGINE=mysql
DB_NAME=<دیتابیس جدا>
DB_USER=<کاربر جدا>
DB_PASSWORD=<رمز دیتابیس>
DB_HOST=localhost
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

## بعد از آپلود (Terminal cPanel)
```bash
source ~/virtualenv/<app_name>/<pyver>/bin/activate
cd ~/apps/university_site
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
mkdir -p tmp && touch tmp/restart.txt
```
سپس در Setup Python App → Restart

## .htaccess
بعد از ساخت اپ در cPanel، مسیرهای `PassengerAppRoot` و `PassengerPython` را با مسیر واقعی همان اپ جدا عوض کنید — نه مسیر سایت اصلی.
