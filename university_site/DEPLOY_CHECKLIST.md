# چک‌لیست دیپلوی — قدم‌به‌قدم (cPanel)

دامنهٔ نمونه در این فایل: `SUBDOMAIN.YOURDOMAIN.IR`  
قبل از شروع، ساب‌دامین واقعی را جایگزین کنید (مثلاً `portal.aab.ac.ir`).

من از اینجا **نمی‌توانم** وارد cPanel شما شوم؛ کارهای سرور را خودتان با این ترتیب انجام دهید.
کارهای آماده‌سازی کد (migration و گیت) را جدا انجام می‌دهیم.

---

## قدم ۰ — روی سیستم خودتان (قبل از آپلود)

1. مطمئن شوید migrationها روی گیت هستند و پوش شده‌اند.
2. فایل `env.production.example` را باز کنید و با دامنه/دیتابیس خودتان پر کنید → روی سرور با نام `.env` ذخیره کنید (هرگز داخل گیت نگذارید).

---

## قدم ۱ — ساب‌دامین جدا

1. وارد cPanel شوید.
2. **Domains → Create a New Domain / Subdomain**
3. نام مثلاً: `portal.yourdomain.ir`
4. Document Root را مسیر **جدید و خالی** بگذارید، مثلاً:
   - `/home/USERNAME/apps/university_site` (بهتر)
   - یا `public_html/portal` فقط اگر خالی است
5. **هرگز** روی ریشه `public_html` سایت اصلی علامه امینی آپلود نکنید.

---

## قدم ۲ — دیتابیس MySQL جدا

1. cPanel → **MySQL® Databases**
2. یک Database جدید بسازید (نام جدا از سایت اصلی)
3. یک User جدید بسازید و رمز قوی بدهید
4. User را به Database با **ALL PRIVILEGES** وصل کنید
5. این سه مقدار را یادداشت کنید: `DB_NAME` / `DB_USER` / `DB_PASSWORD`

---

## قدم ۳ — Python App

1. cPanel → **Setup Python App**
2. Create Application:
   - Application URL = همان ساب‌دامین
   - Application root = همان پوشهٔ جدا
   - Startup file = `passenger_wsgi.py`
   - Entry point = `application`
   - Python = 3.11 (یا نزدیک‌ترین)
3. Create → سپس مسیر virtualenv را یادداشت کنید

---

## قدم ۴ — آپلود کد

یکی از روش‌ها:

**الف) Git روی سرور (اگر فعال است)**
```bash
cd ~/apps
git clone https://github.com/Davoadeivai/university-site.git
# سپس محتویات university_site را به Application root منتقل کنید
```

**ب) آپلود ZIP از سیستم خودتان**
- فقط پوشهٔ `university_site` را zip کنید (بدون `venv` و بدون `.env` لوکال)
- در File Manager داخل Application root استخراج کنید

---

## قدم ۵ — فایل `.env` روی سرور

1. در ریشهٔ اپ (کنار `manage.py`) فایل `.env` بسازید
2. محتوای `env.production.example` را کپی کنید و مقادیر را پر کنید:

```env
SECRET_KEY=<<<از دستور زیر بسازید>>>
DEBUG=False
ALLOWED_HOSTS=portal.yourdomain.ir
CSRF_TRUSTED_ORIGINS=https://portal.yourdomain.ir
DB_ENGINE=mysql
DB_NAME=...
DB_USER=...
DB_PASSWORD=...
DB_HOST=localhost
DB_PORT=3306
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

ساخت SECRET_KEY روی سرور:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## قدم ۶ — نصب پکیج‌ها + migrate + collectstatic + سوپریوزر

در Terminal cPanel:

```bash
source ~/virtualenv/NAMED_APP/3.11/bin/activate
cd ~/apps/university_site   # یا مسیر واقعی Application root

pip install -r requirements.txt

# اگر نصب kavenegar از git خطا داد:
# pip install kavenegar==1.1.2

python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser

mkdir -p tmp
touch tmp/restart.txt
```

سپس در Setup Python App → **Restart**

---

## قدم ۷ — SSL

1. cPanel → **SSL/TLS Status** یا Let's Encrypt
2. برای ساب‌دامین گواهی فعال کنید
3. سایت را با `https://` باز کنید

---

## قدم ۸ — تست سریع بعد از بالا آمدن

- [ ] صفحه اصلی باز می‌شود
- [ ] `/static/css/main.css` لود می‌شود (بدون 404)
- [ ] `/admin/` با سوپریوزر لاگین می‌شود
- [ ] فرم پذیرش OTP (اگر SMS فعال است)
- [ ] آپلود یک تصویر در ادمین و نمایش در media

---

## SMS (اختیاری ولی برای OTP لازم)

بعد از بالا آمدن سایت:

```env
SMS_ENABLED=True
KAVENEGAR_API_KEY=...
KAVENEGAR_OTP_TEMPLATE=نام_الگوی_تأیید_شده
SMS_SENDER_NUMBER=خط_اختصاصی_درصورت_داشتن
SMS_SITE_LABEL=موسسه آموزش عالی علامه امینی بهنمیر
```

سپس `touch tmp/restart.txt`

---

## اگر خطا دیدید

| علامت | کار |
|--------|-----|
| 500 | `logs/django.log` را بخوانید |
| DisallowedHost | `ALLOWED_HOSTS` را اصلاح کنید |
| CSRF failed | `CSRF_TRUSTED_ORIGINS` با https درست باشد |
| static 404 | دوباره `collectstatic` + restart |
| DB connection | نام/یوزر/رمز/هاست MySQL |

---

## چه چیزی را به من بگویید تا دقیق‌تر کنم

 sabدامین واقعی‌تان را بفرستید (مثلاً `portal.example.ir`) تا یک `.env` آمادهٔ کپی‌پیست مخصوص همان دامنه برایتان بنویسم.
