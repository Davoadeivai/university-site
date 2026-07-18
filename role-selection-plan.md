# Role Selection on Register & Login Plan

## Overview

اضافه کردن انتخاب نقش به صفحات ثبت‌نام و ورود با رابط کاربری کارت‌محور (card-style). کاربر نقش خود را با کلیک روی کارت انتخاب می‌کند، سپس فیلدهای مخصوص آن نقش به صورت dynamic نمایش داده می‌شود. نقش در هنگام ثبت‌نام در `UserProfile` ذخیره می‌شود و در هنگام ورود برای redirect به داشبورد مناسب استفاده می‌شود.

### نقش‌ها و فیلدهای اختصاصی:
| نقش | مقدار DB | فیلدهای اضافی در ثبت‌نام |
|-----|----------|--------------------------|
| دانشجو | `student` | شماره دانشجویی، دانشکده |
| استاد | `professor` | کد استادی، دانشکده |
| مدیر دانشگاه | `staff` | واحد سازمانی |
| ادمین | `admin` | — (بدون فیلد اضافی) |

---

## Sub-Task 1: تغییر `register_view` برای دریافت نقش و فیلدهای اضافی

**Status**: [ ] pending

### Intent
`register_view` باید فیلد `role` و فیلدهای شرطی (student_id, department) را از POST دریافت کند، اعتبارسنجی کند، و در `UserProfile` ذخیره کند.

### Expected Outcomes
- فیلد `role` از فرم ثبت‌نام دریافت شده و در `UserProfile.role` ذخیره شود
- فیلد `student_id` برای نقش‌های student و professor اجباری باشد
- فیلد `department` برای همه نقش‌ها (به جز admin) دریافت شود
- اعتبارسنجی: اگر student/professor شد و student_id خالی بود، خطا نمایش داده شود
- نقش `admin` از طریق فرم ثبت‌نام عمومی قابل انتخاب نباشد (فقط از پنل ادمین)

### Todo List
1. در [`university_site/accounts/views.py`](university_site/accounts/views.py) در `register_view`:
   - `role = request.POST.get('role', 'student')` دریافت کنید
   - اعتبارسنجی: role باید یکی از `['student', 'professor', 'staff']` باشد (admin مجاز نیست)
   - `student_id = request.POST.get('student_id', '').strip()`
   - `department = request.POST.get('department', '').strip()`
   - بعد از `UserProfile.objects.get_or_create(user=user)`: فیلدهای role, student_id, department را set و save کنید

### Relevant Context
- [`university_site/accounts/views.py`](university_site/accounts/views.py) — `register_view` خط ۴۱
- [`university_site/accounts/models.py`](university_site/accounts/models.py) — `UserProfile.ROLE_CHOICES` خط ۷

---

## Sub-Task 2: بروزرسانی تمپلیت ثبت‌نام با انتخاب نقش

**Status**: [ ] pending

### Intent
صفحه ثبت‌نام باید ابتدا ۳ کارت (دانشجو / استاد / مدیر دانشگاه) نشان دهد. کاربر روی کارت کلیک می‌کند — کارت highlighted می‌شود، input hidden نقش set می‌شود، و فیلدهای اختصاصی آن نقش با animation ظاهر می‌شوند.

### Expected Outcomes
- ۳ کارت با آیکون، عنوان، و توضیح کوتاه در بالای فرم
- کارت انتخاب‌شده با border رنگی و تیک ✓ مشخص شود
- بعد از انتخاب نقش، فیلدهای اختصاصی نمایش داده شوند:
  - **دانشجو**: شماره دانشجویی (اجباری) + دانشکده
  - **استاد**: کد استادی (اجباری) + دانشکده
  - **مدیر دانشگاه**: واحد سازمانی
- input hidden با نام `role` مقدار انتخاب‌شده را نگه دارد
- بدون انتخاب نقش، دکمه ثبت‌نام غیرفعال (disabled) باشد
- فیلد `username` (نام کاربری) حذف شده و به جایش فیلد کد ملی باشد (طبق پلن قبلی)

### Todo List
1. در [`university_site/templates/accounts/register.html`](university_site/templates/accounts/register.html):
   - بخش انتخاب نقش با ۳ کارت Bootstrap در بالای فرم اضافه کنید
   - input `hidden` با `name="role"` و `id="role-input"` اضافه کنید
   - div های شرطی برای فیلدهای هر نقش با `display:none` پیش‌فرض اضافه کنید
   - JavaScript: تابع `selectRole(role)` برای toggle کارت‌ها و نمایش/پنهان فیلدها
   - دکمه ثبت‌نام: `disabled` تا نقش انتخاب شود
   - فیلد `username` را حذف و `national_id` (کد ملی) جایگزین کنید

### Relevant Context
- [`university_site/templates/accounts/register.html`](university_site/templates/accounts/register.html)

---

## Sub-Task 3: بروزرسانی صفحه ورود با انتخاب نقش

**Status**: [ ] pending

### Intent
صفحه ورود هم ۴ کارت نقش نشان دهد. بعد از انتخاب نقش، فرم کد ملی + رمز عبور نمایش داده شود. نقش انتخاب‌شده در login_view استفاده شود تا بعد از ورود به داشبورد مناسب redirect شود.

### Expected Outcomes
- ۴ کارت (دانشجو / استاد / مدیر دانشگاه / ادمین) با آیکون در بالای فرم ورود
- بعد از انتخاب کارت، بخش فرم کد ملی + رمز عبور با animation slide-down نمایش داده شود
- نقش انتخاب‌شده به عنوان `hidden input` در POST ارسال شود
- `login_view` نقش را بررسی کند: اگر کاربر ورود کرد ولی نقشش با انتخاب‌شده فرق داشت، پیام خطا نشان داده شود
- Redirect بعد از ورود بر اساس نقش:
  - `student` → `/dashboard/`
  - `professor` → `/dashboard/`
  - `staff` → `/dashboard/`
  - `admin` → `/admin/`

### Todo List
1. در [`university_site/templates/accounts/login.html`](university_site/templates/accounts/login.html):
   - ۴ کارت نقش با آیکون اضافه کنید (در بالای فرم)
   - بخش فرم ورود را در یک div با `display:none` قرار دهید
   - JavaScript: `selectRole(role)` که کارت را highlight کند و فرم را نمایش دهد
   - hidden input با `name="role"` اضافه کنید
   - فیلد `username` را به `national_id` تغییر دهید (label «کد ملی»)
2. در [`university_site/accounts/views.py`](university_site/accounts/views.py) در `login_view`:
   - `role = request.POST.get('role', '')` دریافت کنید
   - بعد از authenticate موفق: `user.profile.role` با `role` مقایسه شود
   - اگر نقش اشتباه بود: پیام خطای مناسب («شما با نقش دانشجو ثبت‌نام کرده‌اید»)
   - redirect بر اساس نقش: admin → `/admin/`، بقیه → `/dashboard/`

### Relevant Context
- [`university_site/templates/accounts/login.html`](university_site/templates/accounts/login.html)
- [`university_site/accounts/views.py`](university_site/accounts/views.py) — `login_view` خط ۱۵

---

## نکات طراحی UI

- کارت‌ها: Bootstrap card با hover effect، border رنگی هنگام انتخاب (`border-primary`)
- تیک ✓ در گوشه بالا-راست کارت انتخاب‌شده با رنگ سبز
- آیکون‌های FontAwesome پیشنهادی:
  - دانشجو: `fa-user-graduate`
  - استاد: `fa-chalkboard-teacher`
  - مدیر دانشگاه: `fa-building`
  - ادمین: `fa-user-shield`
- انتقال بین مراحل با CSS transition/animation روان
- موبایل‌پسند: کارت‌ها در موبایل به صورت ۲×۲ grid

---

## ترتیب اجرا

Sub-Task 1 (view) و Sub-Task 2 (تمپلیت ثبت‌نام) مرتبط هستند — باید با هم اجرا شوند.
Sub-Task 3 (تمپلیت + view ورود) می‌تواند بعد از Sub-Task 1 انجام شود.
