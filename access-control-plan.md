# Access Control & Activity Logging Plan

## Overview

این پلن شامل سه بخش اصلی است:
1. **تغییر نقش‌ها** — تغییر نام نقش `staff` به «مدیر دانشگاه»
2. **ورود با کد ملی** — تغییر سیستم ورود به گونه‌ای که کاربران با کد ملی (به عنوان username) وارد شوند
3. **ثبت فعالیت‌ها** — ایجاد مدل `ActivityLog` و ثبت خودکار ورود، خروج، و عملیات مهم

---

## Sub-Task 1: تغییر نام نقش staff

**Status**: [ ] pending

### Intent
نقش `staff` در `UserProfile.ROLE_CHOICES` به «مدیر دانشگاه» تغییر نام پیدا کند تا با نیاز پروژه مطابقت داشته باشد.

### Expected Outcomes
- در پنل ادمین و رابط کاربری، به جای «کارمند» نوشته شود «مدیر دانشگاه»
- مقدار داخلی در دیتابیس همچنان `staff` بماند (بدون نیاز به migration داده)

### Todo List
1. در [`university_site/accounts/models.py`](university_site/accounts/models.py) در `ROLE_CHOICES`، تغییر `('staff', 'کارمند')` به `('staff', 'مدیر دانشگاه')`
2. بررسی اینکه آیا در جای دیگری از کدبیس به نمایش «کارمند» اشاره شده و در صورت نیاز اصلاح شود

### Relevant Context
- [`university_site/accounts/models.py`](university_site/accounts/models.py) — خط ۱۰: `('staff', 'کارمند')`

---

## Sub-Task 2: ورود با کد ملی

**Status**: [ ] pending

### Intent
تغییر `login_view` و `register_view` تا کاربران با کد ملی (که در فیلد `username` ذخیره می‌شود) و رمز عبور وارد شوند. فرم ورود باید label «کد ملی» نشان دهد.

### Expected Outcomes
- فرم ورود «کد ملی» می‌خواهد به جای «نام کاربری»
- `username` در هنگام ثبت‌نام برابر کد ملی وارد شده باشد
- اعتبارسنجی کد ملی (۱۰ رقم عددی) هنگام ثبت‌نام اضافه شود
- `national_id` در `UserProfile` نیز همزمان با کد ملی وارد شده پر شود
- خطای مناسب برای کد ملی تکراری نمایش داده شود

### Todo List
1. در [`university_site/accounts/views.py`](university_site/accounts/views.py):
   - در `login_view`: فیلد form باید `national_id` بگیرد (POST key: `national_id`) و به عنوان `username` به `authenticate` بدهد
   - در `register_view`: فیلد `username` را حذف، فیلد `national_id` اضافه کنید؛ `username=national_id` در `create_user`؛ `national_id` را در `UserProfile` ذخیره کنید؛ اعتبارسنجی ۱۰ رقم عددی اضافه شود
2. در [`university_site/templates/accounts/login.html`](university_site/templates/accounts/login.html): فیلد `username` را به `national_id` تغییر دهید با label «کد ملی»
3. در [`university_site/templates/accounts/register.html`](university_site/templates/accounts/register.html): فیلد `username` را حذف، فیلد `national_id` با label «کد ملی» اضافه کنید

### Relevant Context
- [`university_site/accounts/views.py`](university_site/accounts/views.py) — `login_view` (خط ۱۵)، `register_view` (خط ۴۱)
- [`university_site/accounts/models.py`](university_site/accounts/models.py) — فیلد `national_id` در `UserProfile` (خط ۲۰)

---

## Sub-Task 3: مدل ActivityLog

**Status**: [ ] pending

### Intent
ایجاد مدل `ActivityLog` در اپ `accounts` برای ثبت تمام فعالیت‌های کاربران با تاریخ، ساعت، IP، و نوع عملیات.

### Expected Outcomes
- مدل `ActivityLog` با فیلدهای زیر در دیتابیس ایجاد شود:
  - `user` (FK به User)
  - `action` (نوع عملیات: login, logout, profile_update, request_submit, page_view_important)
  - `description` (توضیح اضافه، اختیاری)
  - `ip_address` (آدرس IP کاربر)
  - `timestamp` (تاریخ و ساعت دقیق — auto)
- Migration ایجاد شود
- مدل در `admin.py` ثبت شود با فیلتر بر اساس `action`، `user`، و تاریخ

### Todo List
1. در [`university_site/accounts/models.py`](university_site/accounts/models.py): مدل `ActivityLog` اضافه کنید
2. اجرای `makemigrations accounts` و `migrate`
3. در [`university_site/accounts/admin.py`](university_site/accounts/admin.py): کلاس `ActivityLogAdmin` اضافه کنید با `list_display`, `list_filter`, `search_fields`, `date_hierarchy`, و readonly

### Relevant Context
- [`university_site/accounts/models.py`](university_site/accounts/models.py)
- [`university_site/accounts/admin.py`](university_site/accounts/admin.py)

---

## Sub-Task 4: ثبت خودکار فعالیت‌ها در Views

**Status**: [ ] pending

### Intent
در تمام view های مرتبط، فراخوانی `ActivityLog.objects.create(...)` اضافه شود تا عملیات مهم ثبت گردد.

### Expected Outcomes
- **ورود**: هنگام login موفق، یک رکورد `action='login'` ثبت شود
- **خروج**: هنگام logout، یک رکورد `action='logout'` ثبت شود
- **ویرایش پروفایل**: هنگام POST موفق در profile view، یک رکورد `action='profile_update'` ثبت شود
- **ثبت درخواست**: در `admissions/views.py` هنگام submit موفق application، یک رکورد `action='request_submit'` ثبت شود
- IP از `request.META.get('REMOTE_ADDR')` یا `X-Forwarded-For` header گرفته شود

### Todo List
1. یک utility function مثل `log_activity(user, action, description, request)` در فایل جداگانه مثل [`university_site/accounts/utils.py`](university_site/accounts/utils.py) ایجاد کنید
2. در [`university_site/accounts/views.py`](university_site/accounts/views.py):
   - در `login_view`: بعد از `login(request, user)` فراخوانی `log_activity` اضافه کنید
   - در `logout_view`: قبل از `logout(request)` فراخوانی `log_activity` اضافه کنید
   - در `profile` view (POST): بعد از ذخیره موفق، `log_activity` اضافه کنید
3. در `admissions/views.py`: هنگام submit موفق، `log_activity` فراخوانی کنید

### Relevant Context
- [`university_site/accounts/views.py`](university_site/accounts/views.py)
- [`university_site/admissions/views.py`](university_site/admissions/views.py)

---

## Sub-Task 5: داشبورد بر اساس نقش

**Status**: [ ] pending

### Intent
`dashboard` view باید بر اساس نقش کاربر، محتوای متفاوتی نمایش دهد — دانشجو، استاد، مدیر دانشگاه (staff)، و ادمین هر کدام اطلاعات متناسب با نقش خود ببینند.

### Expected Outcomes
- ادمین: همه آمارها و لینک پنل مدیریت
- مدیر دانشگاه (staff): آمار کلی دانشگاه
- استاد: دروس، دانشجویان، تکالیف مربوط به خودش
- دانشجو: نمرات، درخواست‌ها، اطلاعیه‌های مربوط به خودش
- view باید نقش کاربر را چک کند و context متناسب به template بفرستد

### Todo List
1. در [`university_site/dashboard/views.py`](university_site/dashboard/views.py): role-based context logic اضافه کنید — `user.profile.role` چک شود و context متناسب برگردانده شود
2. در [`university_site/templates/dashboard/dashboard.html`](university_site/templates/dashboard/dashboard.html): با استفاده از template tag `{% if profile.role == 'student' %}` بلوک‌های متفاوت نمایش دهید

### Relevant Context
- [`university_site/dashboard/views.py`](university_site/dashboard/views.py)
- [`university_site/dashboard/models.py`](university_site/dashboard/models.py) — مدل‌های Enrollment، TeachingAssignment

---

## Notes برای پیاده‌سازی
- اجرای migration بعد از Sub-Task 3 الزامی است قبل از شروع Sub-Task 4
- Sub-Task 1 و 2 مستقل هستند و می‌توانند همزمان اجرا شوند
- Sub-Task 3 باید قبل از Sub-Task 4 تمام شود
- Sub-Task 5 مستقل از بقیه است
