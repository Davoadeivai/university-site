# دیپلوی روی ساب‌دامین (جدا از سایت قبلی)

رمز و اطلاعات ورود را اینجا ننویسید.

## ایده
- سایت قبلی روی دامنه اصلی بماند
- این پروژه روی مثلاً `university.yourdomain.ir` یا پوشه جدا

## cPanel
1. Domains → Create subdomain (مثلاً `university`) با document root جدا
2. Setup Python App → Application URL = همان ساب‌دامین
3. Application root را روی همان document root بگذارید
4. Startup: `passenger_wsgi.py` / Entry: `application`

## DNS (در صورت نیاز)
اگر ساب‌دامین خودکار کار نکرد، در NIC یک رکورد A برای `university` به IP سرور بسازید.

## جداسازی دیتابیس
دیتابیس و کاربر جدا برای این پروژه بسازید تا با سایت قبلی قاطی نشود.
