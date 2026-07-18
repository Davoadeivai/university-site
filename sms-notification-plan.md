# SMS Notification System Plan

## Overview

این پلن سیستم اطلاع‌رسانی پیامکی کامل را با استفاده از سرویس **کاوه‌نگار (Kavenegar)** پیاده‌سازی می‌کند. یک اپ مجزا به نام `notifications` ایجاد می‌شود که لایه SMS را مدیریت کرده و در تمام اپ‌های پروژه استفاده می‌شود.

### موارد ارسال پیامک:
1. **بازیابی رمز عبور** — OTP به جای یا علاوه بر لینک ایمیل
2. **انتخاب واحد** — تأیید ثبت‌نام در درس
3. **اخبار جدید** — به محض publish، برای همه کاربران دارای شماره موبایل
4. **اطلاعیه‌ها** — اطلاعیه‌های فوری از Announcement
5. **وضعیت درخواست پذیرش** — تأیید/رد/در حال بررسی
6. **یادآوری امتحان** — زمان و مکان امتحان
7. **پرداخت** — تأیید پرداخت شهریه

---

## Sub-Task 1: نصب و پیکربندی کاوه‌نگار

**Status**: [ ] pending

### Intent
افزودن پکیج کاوه‌نگار به پروژه و تنظیم API Key در settings و .env

### Expected Outcomes
- پکیج `kavenegar` در `requirements.txt` اضافه شود
- متغیرهای محیطی `KAVENEGAR_API_KEY` و `SMS_SENDER_NUMBER` در `config/settings.py` و `.env.example` تعریف شوند

### Todo List
1. در [`university_site/requirements.txt`](university_site/requirements.txt): خط `kavenegar` اضافه کنید
2. در [`university_site/config/settings.py`](university_site/config/settings.py): تنظیمات زیر اضافه کنید:
   ```
   KAVENEGAR_API_KEY = config('KAVENEGAR_API_KEY', default='')
   SMS_SENDER_NUMBER = config('SMS_SENDER_NUMBER', default='')
   SMS_ENABLED = config('SMS_ENABLED', default=False, cast=bool)
   ```
3. در [`university_site/.env.example`](university_site/.env.example): متغیرهای زیر اضافه کنید:
   ```
   KAVENEGAR_API_KEY=your-api-key-here
   SMS_SENDER_NUMBER=your-sender-number
   SMS_ENABLED=True
   ```

### Relevant Context
- [`university_site/config/settings.py`](university_site/config/settings.py)
- [`university_site/requirements.txt`](university_site/requirements.txt)

---

## Sub-Task 2: ایجاد اپ notifications و SMSService

**Status**: [ ] pending

### Intent
ایجاد اپ `notifications` با یک لایه abstraction برای ارسال پیامک از طریق کاوه‌نگار. این لایه در تمام اپ‌ها استفاده می‌شود.

### Expected Outcomes
- اپ `notifications` ایجاد شود
- فایل `notifications/sms.py` با کلاس `SMSService` ایجاد شود که شامل متدهای زیر باشد:
  - `send_otp(phone, code)` — ارسال کد تأیید
  - `send_message(phone, message)` — ارسال پیام تک‌نفره
  - `send_bulk(phones, message)` — ارسال پیام به لیست شماره‌ها
- مدل `SMSLog` برای ثبت تمام پیامک‌های ارسال‌شده (وضعیت، متن، شماره، زمان)
- اپ در `INSTALLED_APPS` ثبت شود

### Todo List
1. ایجاد اپ: `python manage.py startapp notifications` در پوشه `university_site/`
2. ایجاد [`university_site/notifications/sms.py`](university_site/notifications/sms.py):
   - import کاوه‌نگار
   - بررسی `SMS_ENABLED` — اگر False باشد فقط log کند
   - متد `send_otp`, `send_message`, `send_bulk`
   - try/except برای خطاهای API کاوه‌نگار با ثبت در log
3. ایجاد مدل `SMSLog` در [`university_site/notifications/models.py`](university_site/notifications/models.py):
   - فیلدها: `recipient_phone`, `message`, `status (sent/failed)`, `error_message`, `sent_at`
4. ایجاد [`university_site/notifications/admin.py`](university_site/notifications/admin.py): ثبت SMSLog با `list_display`, `list_filter`, `date_hierarchy`
5. اضافه کردن `notifications` به `INSTALLED_APPS` در [`university_site/config/settings.py`](university_site/config/settings.py)
6. اجرای `makemigrations notifications` و `migrate`

### Relevant Context
- [`university_site/config/settings.py`](university_site/config/settings.py) — INSTALLED_APPS

---

## Sub-Task 3: پیامک بازیابی رمز عبور (OTP)

**Status**: [ ] pending

### Intent
جایگزین‌کردن بازیابی رمز عبور ایمیل‌محور با OTP پیامکی. کاربر کد ملی وارد می‌کند، کد ۶ رقمی به شماره موبایل ثبت‌شده‌اش ارسال می‌شود.

### Expected Outcomes
- مدل `OTPCode` برای ذخیره کد موقت با مدت اعتبار ۱۰ دقیقه
- فرم درخواست بازیابی رمز: کد ملی می‌گیرد، کد OTP به موبایل ارسال می‌کند
- فرم تأیید OTP: کد + رمز جدید می‌گیرد
- فلوی ایمیلی موجود حفظ شود (fallback)

### Todo List
1. مدل `OTPCode` در [`university_site/notifications/models.py`](university_site/notifications/models.py):
   - فیلدها: `user (FK)`, `code (6-digit)`, `created_at`, `expires_at`, `is_used`
   - متد `is_valid()` برای بررسی انقضا
2. در [`university_site/accounts/views.py`](university_site/accounts/views.py):
   - `password_reset_by_sms()` view: کد ملی می‌گیرد → کاربر را پیدا می‌کند → کد OTP تولید → با `SMSService.send_otp()` ارسال
   - `password_reset_otp_confirm()` view: کد OTP را تأیید می‌کند → رمز جدید ثبت → OTP را used می‌کند
3. در [`university_site/accounts/urls.py`](university_site/accounts/urls.py): دو URL جدید اضافه کنید
4. تمپلیت‌های جدید:
   - `accounts/password_reset_sms.html` — فرم ورود کد ملی
   - `accounts/password_reset_otp.html` — فرم تأیید OTP و رمز جدید
5. در تمپلیت `accounts/login.html`: لینک «بازیابی با پیامک» اضافه کنید

### Relevant Context
- [`university_site/accounts/views.py`](university_site/accounts/views.py) — `password_reset_request` (خط ۹۱)
- [`university_site/accounts/urls.py`](university_site/accounts/urls.py)
- [`university_site/accounts/models.py`](university_site/accounts/models.py) — فیلد `phone` و `national_id` در UserProfile

---

## Sub-Task 4: پیامک انتخاب واحد (Enrollment)

**Status**: [ ] pending

### Intent
هنگامی که دانشجو در یک درس ثبت‌نام می‌کند (Enrollment ایجاد می‌شود)، پیامک تأیید به شماره موبایلش ارسال شود.

### Expected Outcomes
- پیامک با متن «دانشجوی گرامی، ثبت‌نام شما در درس [نام درس] - [نیمسال] با موفقیت انجام شد»
- در صورت تغییر وضعیت Enrollment (dropped/failed/completed) نیز پیامک اطلاع‌رسانی ارسال شود

### Todo List
1. ایجاد [`university_site/notifications/signals.py`](university_site/notifications/signals.py):
   - Signal `post_save` برای مدل `Enrollment` از `dashboard/models.py`
   - اگر `created=True` و status=registered: `SMSService.send_message()` فراخوانی شود
   - اگر status تغییر کرد به dropped/failed/completed: پیامک وضعیت ارسال شود
2. در [`university_site/notifications/apps.py`](university_site/notifications/apps.py): `ready()` متد برای import سیگنال‌ها
3. ایجاد [`university_site/notifications/messages.py`](university_site/notifications/messages.py): متن‌های استاندارد پیامک‌ها به فارسی

### Relevant Context
- [`university_site/dashboard/models.py`](university_site/dashboard/models.py) — مدل `Enrollment`
- شماره موبایل از `user.profile.phone` گرفته می‌شود

---

## Sub-Task 5: پیامک اخبار جدید

**Status**: [ ] pending

### Intent
به محض publish شدن یک خبر (is_published=True)، پیامک خلاصه خبر برای تمام کاربران دارای شماره موبایل ارسال شود. ادمین نیز بتواند از پنل مدیریت دستی ارسال کند.

### Expected Outcomes
- Signal `post_save` بر روی مدل `News`: اگر `is_published` تازه True شد → bulk SMS
- Action اضافه در `NewsAdmin`: «ارسال پیامک این خبر» که manual trigger می‌دهد
- متن پیامک: «خبر جدید دانشگاه: [عنوان خبر] — [لینک کوتاه]»

### Todo List
1. در [`university_site/notifications/signals.py`](university_site/notifications/signals.py):
   - Signal `post_save` برای مدل `News`
   - بررسی `instance.is_published` و `not created` (تغییر از False به True)
   - دریافت شماره‌های همه کاربران فعال: `UserProfile.objects.filter(phone__regex=r'^09[0-9]{9}$').values_list('phone', flat=True)`
   - فراخوانی `SMSService.send_bulk(phones, message)`
2. در [`university_site/news/admin.py`](university_site/news/admin.py):
   - `admin action` با نام `send_sms_notification` اضافه کنید
   - در این action: `SMSService.send_bulk()` فراخوانی کنید
3. در [`university_site/notifications/messages.py`](university_site/notifications/messages.py): متن پیامک خبر تعریف شود

### Relevant Context
- [`university_site/news/models.py`](university_site/news/models.py) — فیلد `is_published`
- [`university_site/news/admin.py`](university_site/news/admin.py)

---

## Sub-Task 6: پیامک اطلاعیه‌های فوری و سایر موارد

**Status**: [ ] pending

### Intent
سایر موارد مهم پیامکی را پوشش دهد: اطلاعیه‌های Announcement، تغییر وضعیت درخواست پذیرش، یادآوری امتحان، و تأیید پرداخت شهریه.

### Expected Outcomes
- **اطلاعیه** (`Announcement`): وقتی `is_active=True` می‌شود، بر اساس `target` به گروه مربوطه پیامک ارسال شود
- **پذیرش** (`Application`): وقتی وضعیت به accepted/rejected تغییر می‌کند، پیامک به ایمیل/موبایل درخواست‌دهنده ارسال شود
- **یادآوری امتحان** (`ExamSchedule`): یادآوری ۲۴ ساعت قبل از امتحان — به صورت admin action
- **پرداخت** (`Payment`): وقتی `is_paid=True` می‌شود، رسید پیامکی ارسال شود

### Todo List
1. در [`university_site/notifications/signals.py`](university_site/notifications/signals.py): سیگنال‌های زیر اضافه کنید:
   - `Announcement post_save` → فیلتر بر اساس target → send_bulk به گروه مناسب
   - `Application post_save` → اگر status تغییر کرد → send_message به موبایل متقاضی
   - `Payment post_save` → اگر is_paid=True شد → send_message به دانشجو
2. در [`university_site/dashboard/admin.py`](university_site/dashboard/admin.py): admin action برای ExamSchedule جهت ارسال یادآوری پیامکی

### Relevant Context
- [`university_site/accounts/models.py`](university_site/accounts/models.py) — مدل `Announcement`
- [`university_site/admissions/models.py`](university_site/admissions/models.py) — مدل `Application`
- [`university_site/dashboard/models.py`](university_site/dashboard/models.py) — مدل `Payment`, `ExamSchedule`

---

## نکات مهم پیاده‌سازی

- **SMS_ENABLED=False** در محیط development — فقط لاگ می‌کند، پیامک واقعی نمی‌فرستد
- **شماره موبایل**: اعتبارسنجی regex فرمت `09XXXXXXXXX` قبل از ارسال
- **Bulk SMS**: کاوه‌نگار محدودیت تعداد در هر درخواست دارد — در صورت تعداد زیاد باید به دسته‌های ۱۰۰ تایی تقسیم شود
- **ترتیب اجرا**: Sub-Task 1 → Sub-Task 2 → بقیه به صورت موازی
- هیچ Celery یا task queue نیاز نیست — ارسال synchronous است (در آینده قابل upgrade)
