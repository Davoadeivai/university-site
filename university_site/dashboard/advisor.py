"""راهنمای انتخاب واحد — «الان کدام درس‌ها؟»

چرا
───
صفحهٔ انتخاب واحد همهٔ دروس رشته را پشت سر هم می‌ریزد؛ برای یک
کارشناسی پیوسته یعنی حدود چهل ردیف. پیش‌نیاز و تداخل و ظرفیت از
قبل بررسی می‌شوند (`enrollment_rules`) و دلیل قفل‌بودن هم نوشته
می‌شود — چیزی که کم بود، ترتیب است: دانشجوی ترم سه باید بداند
کدام شش درس مالِ حالای اوست.

`Course.semester` همان ترم‌بندی است و از قبل در پایگاه داده هست.
اینجا فقط از آن استفاده می‌شود؛ جدول تازه‌ای ساخته نمی‌شود.

ترم دانشجو چطور حساب می‌شود
───────────────────────────
از روی درس‌های پاس‌شده، نه از روی تاریخ ثبت‌نام: دانشجویی که یک
ترم مرخصی گرفته یا درسی افتاده، با تاریخ جلوتر می‌رود ولی در عمل
نرفته است. بالاترین ترمی که دانشجو از آن درسی پاس کرده، به‌اضافهٔ
یک — و اگر هنوز چیزی پاس نکرده، ترم ۱.
"""
from __future__ import annotations

# چند ردیف پیشنهاد نشان داده شود
SUGGESTION_LIMIT = 8


def current_term(student, major=None) -> int:
    """ترمی که دانشجو عملاً در آن است — دست‌کم ۱."""
    from .models import Enrollment

    qs = (
        Enrollment.objects
        .filter(student=student, final_grade__isnull=False)
        .select_related('course')
    )
    if major is not None:
        qs = qs.filter(course__major=major)

    passed = [
        e.course.semester for e in qs
        if e.course_id and float(e.final_grade) >= 10
    ]
    return max(passed) + 1 if passed else 1


def group_rows(rows: list[dict], term: int) -> dict:
    """ردیف‌های صفحهٔ انتخاب واحد را به سه دستهٔ معنادار می‌شکند.

    - `suggested`: مالِ همین ترم و قابل انتخاب — کاری که باید بکند
    - `available`: از ترم‌های دیگر ولی الان قابل انتخاب (افتاده یا جلو افتاده)
    - `later`: قفل است؛ دلیلش کنارش نوشته شده

    ردیف‌های گرفته‌شده در هیچ‌کدام نیستند: آن‌ها در جدول «دروس
    انتخاب‌شده» دیده می‌شوند و تکرارشان اینجا فقط شلوغی است.
    """
    suggested, available, later = [], [], []
    for row in rows:
        if row.get('enrolled'):
            continue
        if row.get('blocked'):
            later.append(row)
        elif getattr(row.get('course'), 'semester', 0) == term:
            suggested.append(row)
        else:
            available.append(row)
    return {
        'suggested': suggested[:SUGGESTION_LIMIT],
        'suggested_total': len(suggested),
        'available': available,
        'later': later,
    }


def build(student, major, rows: list[dict], standing=None) -> dict:
    """همهٔ چیزی که قالب برای نوار راهنما لازم دارد."""
    term = current_term(student, major)
    groups = group_rows(rows, term)

    units = sum(
        row['course'].credits for row in groups['suggested']
    )
    return {
        'term': term,
        'suggested_units': units,
        'max_units': getattr(standing, 'max_units', None),
        'min_units': getattr(standing, 'min_units', None),
        **groups,
    }
