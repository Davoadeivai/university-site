"""نگاشت یکسان واژگان مقطع بین Major، پذیرش و پوشه اسناد."""
from __future__ import annotations

from academics.models import Major

# Major.degree → DownloadableDocument.degree_level
MAJOR_TO_DOCUMENT = {
    'bachelor_cont': 'bachelor_continuous',
    'bachelor_disc': 'bachelor_discontinuous',
    'bachelor': 'bachelor_continuous',
    'associate_cont': 'associate_tech',
    'associate_disc': 'associate',
    'associate': 'associate',
    'master': 'master',
    'phd': 'general',
}

# کدهای درشت پذیرش / فیلتر منو → پیشوندهای Major.degree
COARSE_TO_MAJOR_PREFIXES = {
    'associate': ('associate',),
    'bachelor': ('bachelor',),
    'master': ('master',),
    'phd': ('phd',),
}

# برچسب‌های فیلتر هاب مسیر دانشجو
HUB_DEGREE_FILTERS = [
    ('', 'همه مقاطع'),
    ('associate', 'کاردانی'),
    ('bachelor', 'کارشناسی'),
    ('master', 'کارشناسی ارشد'),
    ('phd', 'دکتری'),
]


def normalize_degree_query(raw: str) -> str:
    """ورودی GET را به کد درشت یا کد دقیق Major تبدیل می‌کند."""
    value = (raw or '').strip().lower().replace('-', '_').replace(' ', '_')
    aliases = {
        'bachelor_continuous': 'bachelor_cont',
        'bachelor_discontinuous': 'bachelor_disc',
        'associate_tech': 'associate_cont',
        'kardani': 'associate',
        'karshenasi': 'bachelor',
        'arshad': 'master',
    }
    return aliases.get(value, value)


def document_degree_for_major(major_degree: str) -> str:
    return MAJOR_TO_DOCUMENT.get(major_degree, 'general')


def document_degree_for_query(raw: str) -> str:
    """برای لینک آیین‌نامه از ?degree= هاب یا Major."""
    code = normalize_degree_query(raw)
    if code in MAJOR_TO_DOCUMENT:
        return MAJOR_TO_DOCUMENT[code]
    if code in ('bachelor_continuous', 'bachelor_discontinuous', 'associate', 'associate_tech', 'master', 'general'):
        return code
    if code in COARSE_TO_MAJOR_PREFIXES:
        # پیش‌فرض پوشه برای فیلتر درشت
        defaults = {
            'associate': 'associate',
            'bachelor': 'bachelor_continuous',
            'master': 'master',
            'phd': 'general',
        }
        return defaults.get(code, 'general')
    return 'general'


def major_degree_q(raw: str):
    """Q-filter برای Major بر اساس ?degree= (درشت یا دقیق)."""
    from django.db.models import Q

    code = normalize_degree_query(raw)
    if not code:
        return Q()
    if code in dict(Major.DEGREE_CHOICES):
        return Q(degree=code)
    prefixes = COARSE_TO_MAJOR_PREFIXES.get(code)
    if prefixes:
        q = Q()
        for p in prefixes:
            q |= Q(degree=p) | Q(degree__startswith=p)
        return q
    return Q(degree=code)


def admission_degree_for_major(major) -> str:
    if major is None:
        return ''
    return getattr(major, 'admission_degree', '') or ''


def hub_degree_label(raw: str) -> str:
    code = normalize_degree_query(raw)
    for key, label in HUB_DEGREE_FILTERS:
        if key == code:
            return label
    return dict(Major.DEGREE_CHOICES).get(code, code or 'همه')
