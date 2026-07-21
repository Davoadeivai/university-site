# دیپلوی جدا از سایت اصلی علامه امینی

## قانون مهم
به هیچ‌وجه این پروژه را داخل ریشه سایت اصلی (`public_html` دامنه اصلی) آپلود یا جایگزین نکنید.
فایل‌های سایت علامه امینی باید دست‌نخورده بمانند.

## روش درست
- دامنه اصلی / `public_html` → سایت فعلی علامه امینی (دست نزنید)
- این پروژه → فقط روی **ساب‌دامین** با Document Root جدا

مثال:
- سایت اصلی: `https://yourdomain.ir` → `public_html/`
- این پروژه: `https://new.yourdomain.ir` → مثلاً `public_html/new` یا بهتر: خارج از public_html مثل `/home/USERNAME/apps/university_site`

## cPanel (بدون دست زدن به سایت اصلی)
1. Domains → Create a New Domain/Subdomain
2. Document Root را مسیر **جدید و خالی** بگذارید (نه ریشه public_html)
3. Setup Python App → Application URL = همان ساب‌دامین
4. Application root = همان Document Root جدید
5. Startup file: `passenger_wsgi.py` — Entry point: `application`
6. دیتابیس MySQL **جدا** بسازید (نام جدا از دیتابیس سایت اصلی)

## DNS
فقط برای ساب‌دامین رکورد A/CNAME بسازید؛ تنظیمات دامنه اصلی را تغییر ندهید مگر لازم باشد.

## چیزهایی که نباید انجام دهید
- آپلود zip روی `public_html` ریشه
- جایگزینی `index.php` / فایل‌های Joomla/WordPress/سایت فعلی
- استفاده از همان دیتابیس سایت اصلی
- ویرایش فایل‌های موجود در ریشه دامنه اصلی
