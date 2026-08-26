"""ساختار معاونت‌ها — یک منبع، برای منو و صفحه.

چرا اینجا و نه در قالب
──────────────────────
ترتیب معاونت‌ها و زیرمجموعه‌هایشان تا امروز در `base.html` دستی
نوشته شده بود و صفحهٔ «معاونت‌ها» جداگانه از دیتابیس می‌خواند. دو
منبع برای یک چیز یعنی دیر یا زود با هم اختلاف پیدا می‌کنند — منو
یک ترتیب نشان می‌داد و صفحه ترتیبی دیگر.

حالا هر دو از همین فایل می‌خوانند. اضافه‌کردن یک زیرمجموعه یک ردیف
اینجاست، نه دو ویرایش در دو جا.

ترتیب همان است که سند اصلاحات موسسه خواسته: آموزشی، پژوهشی،
اداری و مالی، دانشجویی، فنی و عمرانی.
"""
from __future__ import annotations

from django.urls import NoReverseMatch, reverse

# (کلید معاونت، عنوان کوتاه برای منو، آیکون)
VICE_ORDER = [
    ('education',     'معاونت آموزشی',      'fa-graduation-cap'),
    ('research',      'معاونت پژوهشی',      'fa-flask'),
    ('admin_finance', 'معاونت اداری و مالی', 'fa-coins'),
    ('student',       'معاونت دانشجویی',    'fa-user-group'),
    ('construction',  'معاونت فنی و عمرانی', 'fa-helmet-safety'),
]

# زیرمجموعه‌هایی که صفحهٔ ثابت خودشان را دارند (نه ردیف دیتابیس).
# «دفتر همکاری‌های علمی» به درخواست موسسه از حوزهٔ ریاست به اینجا آمد.
STATIC_UNITS = {
    'education': [
        ('تحصیلات تکمیلی', 'core:graduate_studies'),
        ('مدیر تحصیلات تکمیلی', 'core:graduate_manager'),
        ('گروه‌های آموزشی', 'academics:groups_list'),
    ],
    'research': [
        ('دفتر همکاری‌های علمی و بین‌المللی', 'core:international_office'),
        ('منابع پژوهشی', 'directory:resources'),
    ],
}


def _url(name: str) -> str:
    """نشانی یک مسیر نام‌دار؛ اگر نبود، خالی به‌جای پرتاب خطا.

    یک مسیر حذف‌شده نباید کل نوار بالای سایت را از کار بیندازد.
    """
    try:
        return reverse(name)
    except NoReverseMatch:
        return ''


def build(vices_by_type: dict | None = None,
          graduate_groups=None) -> list:
    """فهرست معاونت‌ها به ترتیب سند، با شماره و زیرمجموعه‌ها.

    `vices_by_type` نگاشت کلید معاونت به ردیف دیتابیس است؛ اگر داده
    نشود، خودش می‌خواند. معاونتی که هنوز ردیفی ندارد هم در فهرست
    می‌ماند — صفحه‌اش خودش می‌گوید اطلاعاتش پر نشده، و حذفش از منو
    فقط بازدیدکننده را سردرگم می‌کند.
    """
    from core.models import VicePresidency

    if vices_by_type is None:
        vices_by_type = {
            v.vice_type: v for v in
            VicePresidency.objects.filter(is_active=True)
            .prefetch_related('units')
        }

    rows = []
    for index, (key, label, icon) in enumerate(VICE_ORDER, start=1):
        vice = vices_by_type.get(key)

        children = [
            {'title': title, 'url': _url(name)}
            for title, name in STATIC_UNITS.get(key, [])
        ]
        # گروه‌های دارای تحصیلات تکمیلی زیر معاونت آموزشی می‌آیند
        if key == 'education' and graduate_groups:
            children += [
                {'title': group.name, 'url': group.get_absolute_url()}
                for group in graduate_groups
            ]
        # واحدهای ثبت‌شده در پنل — بدون صفحهٔ اختصاصی، پس بدون لینک
        if vice is not None:
            children += [
                {'title': unit.name, 'url': ''}
                for unit in vice.units.all() if unit.is_active
            ]

        rows.append({
            'number': index,
            'key': key,
            'label': label,
            'icon': icon,
            'vice': vice,
            'url': _vice_url(key),
            'children': children,
        })
    return rows


def _vice_url(key: str) -> str:
    try:
        return reverse('core:vice_detail', args=[key])
    except NoReverseMatch:
        return ''
