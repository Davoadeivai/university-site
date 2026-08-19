"""خط زمانی وضعیت پذیرش — با توضیح هر مرحله و فهرست کمبودها.

چرا
───
هفت وضعیت داریم، ولی صفحهٔ پیگیری فقط اسم وضعیت را می‌گفت. متقاضی
می‌دید «در حال بررسی» و نمی‌دانست یعنی چند روز، و مهم‌تر: وضعیت
«نیاز به تکمیل مدارک» نمی‌گفت **کدام** مدرک. نتیجه‌اش تماس تلفنی
با موسسه بود؛ همان چیزی که یک صفحهٔ پیگیری باید از بین ببرد.

اینجا به هر مرحله یک جملهٔ توضیح می‌چسبد، و برای وضعیت ناقص،
فهرست دقیق چیزهایی که آپلود نشده‌اند از روی خود پرونده ساخته
می‌شود — نه از روی حدس.
"""
from __future__ import annotations

# توضیح هر وضعیت — یک جمله، به زبان متقاضی نه به زبان سامانه
HINTS = {
    'pending': 'درخواست شما ثبت شد و در نوبت بررسی کارشناس است.',
    'reviewing': 'کارشناس پذیرش در حال بررسی مدارک شماست. '
                 'معمولاً ۳ تا ۵ روز کاری طول می‌کشد.',
    'incomplete': 'پرونده ناقص است. موارد زیر را تکمیل کنید تا بررسی ادامه یابد.',
    'interview': 'برای مصاحبه دعوت شده‌اید. تاریخ و ساعت را در همین صفحه ببینید.',
    'accepted': 'پذیرفته شدید. برای ساخت حساب دانشجویی اقدام کنید.',
    'rejected': 'این درخواست پذیرفته نشد. دلیل در همین صفحه آمده است.',
    'waiting': 'در فهرست انتظار هستید. اگر ظرفیتی آزاد شود خبر می‌دهیم.',
}

# فیلدهای مدرک و نامی که متقاضی می‌شناسد
DOCUMENTS = [
    ('doc_national_id', 'تصویر کارت ملی'),
    ('doc_prev_degree', 'تصویر مدرک تحصیلی'),
    ('doc_photo', 'عکس پرسنلی'),
]

# فیلدهای متنی که نبودشان هم پرونده را ناقص می‌کند
REQUIRED_FIELDS = [
    ('national_id', 'کد ملی'),
    ('phone', 'شمارهٔ موبایل'),
    ('address', 'نشانی'),
    ('prev_major', 'رشتهٔ مدرک قبلی'),
    ('gpa', 'معدل'),
]


def missing_items(app) -> list[str]:
    """چه چیزی در پرونده جا مانده — به نامی که متقاضی می‌شناسد.

    مدرک پایان خدمت عمداً اینجا نیست: فقط برای بخشی از متقاضیان
    موضوعیت دارد و خواستنش از همه، پرونده‌های سالم را ناقص نشان
    می‌دهد.
    """
    gaps = []
    for field, label in DOCUMENTS:
        if not getattr(app, field, None):
            gaps.append(label)
    for field, label in REQUIRED_FIELDS:
        value = getattr(app, field, None)
        if value in (None, '', 0):
            gaps.append(label)
    if app.military == 'unknown' and app.gender == 'male':
        gaps.append('وضعیت نظام وظیفه')
    return gaps


def build(app) -> list[dict]:
    """مراحل خط زمانی: هرکدام با کلید، برچسب، وضعیت و توضیح."""
    from .models import Application

    labels = dict(Application.STATUS_CHOICES)

    def step(key, state):
        return {
            'key': key,
            'label': labels.get(key, key),
            'state': state,
            'hint': HINTS.get(key, ''),
        }

    # رد و انتظار پایان مسیرند: نشان‌دادن مراحل بعدی گمراه‌کننده است
    if app.status in ('rejected', 'waiting'):
        return [step(app.status, 'current')]

    if app.status in ('incomplete', 'interview'):
        rows = [
            step('pending', 'done'),
            step('reviewing', 'done'),
            step(app.status, 'current'),
            step('accepted', 'todo'),
        ]
        if app.status == 'incomplete':
            rows[2]['missing'] = missing_items(app)
        return rows

    main_flow = ['pending', 'reviewing', 'accepted']
    try:
        cur = main_flow.index(app.status)
    except ValueError:
        cur = 0
    rows = [
        step(key, 'done' if i < cur else ('current' if i == cur else 'todo'))
        for i, key in enumerate(main_flow)
    ]
    if app.status == 'accepted' and app.interview_date:
        rows.insert(-1, step('interview', 'done'))
    return rows
