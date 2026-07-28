"""نگاشت یکسان واژگان مقطع بین Major، پذیرش، هاب و پوشه اسناد.

مقاطع رسمی سایت:
  ۱. کاردانی پیوسته
  ۲. کارشناسی ناپیوسته
  ۳. کارشناسی پیوسته
  ۴. کاردانی فنی
  ۵. کارشناسی ارشد
"""
from __future__ import annotations

# ترتیب نمایش ثابت (همان ترتیب درخواستی)
CANONICAL_DEGREES = [
    ('associate_cont', 'کاردانی پیوسته'),
    ('bachelor_disc', 'کارشناسی ناپیوسته'),
    ('bachelor_cont', 'کارشناسی پیوسته'),
    ('associate_tech', 'کاردانی فنی'),
    ('master', 'کارشناسی ارشد'),
]

CANONICAL_CODES = {code for code, _ in CANONICAL_DEGREES}

# کدهای قدیمی → کد رسمی
LEGACY_TO_CANONICAL = {
    'associate': 'associate_cont',
    'associate_disc': 'associate_cont',
    'bachelor': 'bachelor_cont',
    'phd': 'master',  # دکتری در UI حذف شده؛ نگاشت ایمن برای دادهٔ قدیمی
    'bachelor_continuous': 'bachelor_cont',
    'bachelor_discontinuous': 'bachelor_disc',
    # اسناد
    'associate_tech': 'associate_tech',
}

# Major.degree → DownloadableDocument.degree_level
MAJOR_TO_DOCUMENT = {
    'associate_cont': 'associate_cont',
    'associate_tech': 'associate_tech',
    'associate_disc': 'associate',  # پوشهٔ قدیمی ناپیوسته
    'associate': 'associate',
    'bachelor_cont': 'bachelor_continuous',
    'bachelor_disc': 'bachelor_discontinuous',
    'bachelor': 'bachelor_continuous',
    'master': 'master',
    'phd': 'general',
}

# فیلتر هاب / منو — فقط مقاطع رسمی
HUB_DEGREE_FILTERS = [('', 'همه مقاطع')] + list(CANONICAL_DEGREES)

# برای فیلتر Major: کد رسمی → کدهای ذخیره‌شدهٔ مجاز
CANONICAL_TO_MAJOR_DEGREES = {
    'associate_cont': ('associate_cont', 'associate', 'associate_disc'),
    'associate_tech': ('associate_tech',),
    'bachelor_cont': ('bachelor_cont', 'bachelor'),
    'bachelor_disc': ('bachelor_disc',),
    'master': ('master',),
}


def to_canonical_degree(raw: str) -> str:
    """هر ورودی را به یکی از ۵ کد رسمی تبدیل می‌کند (یا خالی)."""
    code = normalize_degree_query(raw)
    if not code:
        return ''
    if code in CANONICAL_CODES:
        return code
    mapped = LEGACY_TO_CANONICAL.get(code, '')
    if mapped in CANONICAL_CODES:
        return mapped
    return ''


def normalize_degree_query(raw: str) -> str:
    """ورودی GET را نرمال می‌کند (بدون اجبار به canonical)."""
    value = (raw or '').strip().lower().replace('-', '_').replace(' ', '_')
    aliases = {
        'bachelor_continuous': 'bachelor_cont',
        'bachelor_discontinuous': 'bachelor_disc',
        'kardani_peyvaste': 'associate_cont',
        'kardani_fanni': 'associate_tech',
        'karshenasi_peyvaste': 'bachelor_cont',
        'karshenasi_napivaste': 'bachelor_disc',
        'arshad': 'master',
        'kardani': 'associate_cont',
        'karshenasi': 'bachelor_cont',
    }
    return aliases.get(value, value)


def document_degree_for_major(major_degree: str) -> str:
    return MAJOR_TO_DOCUMENT.get(major_degree, 'general')


def document_degree_for_query(raw: str) -> str:
    """برای لینک آیین‌نامه از ?degree= هاب یا Major."""
    code = normalize_degree_query(raw)
    canonical = to_canonical_degree(code) or code
    if canonical in MAJOR_TO_DOCUMENT:
        return MAJOR_TO_DOCUMENT[canonical]
    if code in (
        'bachelor_continuous', 'bachelor_discontinuous',
        'associate', 'associate_tech', 'associate_cont', 'master', 'general',
    ):
        return code if code != 'associate_cont' else 'associate_cont'
    return 'general'


def major_degree_q(raw: str):
    """Q-filter برای Major بر اساس کد رسمی یا دقیق."""
    from django.db.models import Q

    code = to_canonical_degree(raw) or normalize_degree_query(raw)
    if not code:
        return Q()
    degrees = CANONICAL_TO_MAJOR_DEGREES.get(code)
    if degrees:
        return Q(degree__in=degrees)
    return Q(degree=code)


def admission_degree_for_major(major) -> str:
    if major is None:
        return ''
    deg = getattr(major, 'degree', '') or ''
    return to_canonical_degree(deg) or deg


def hub_degree_label(raw: str) -> str:
    code = to_canonical_degree(raw) or normalize_degree_query(raw)
    for key, label in HUB_DEGREE_FILTERS:
        if key == code:
            return label
    labels = dict(CANONICAL_DEGREES)
    return labels.get(code, code or 'همه')


def degrees_compatible(selected: str, major_degree: str) -> bool:
    """آیا رشته با مقطع انتخاب‌شده هم‌خوان است؟"""
    a = to_canonical_degree(selected)
    b = to_canonical_degree(major_degree) or normalize_degree_query(major_degree)
    if not a:
        return True
    if a == b:
        return True
    # رشته با کد دقیق رسمی
    allowed = CANONICAL_TO_MAJOR_DEGREES.get(a, ())
    return b in allowed or major_degree in allowed
