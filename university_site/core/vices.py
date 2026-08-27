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
    # ساختار دقیقاً از چارت سازمانی موسسه برداشته شده.
    #
    # هر ردیف یک سه‌تایی است: (عنوان، نام مسیر، زیرمجموعه‌ها).
    # نام مسیر خالی یعنی صفحهٔ اختصاصی ندارد و در منو متن ساده
    # می‌شود — لینکی که به ۴۰۴ برسد بدتر از نبودن لینک است.
    #
    # چارت سه سطح دارد (معاونت ← مدیر ← اداره)، پس زیرمجموعه‌ها هم
    # تودرتو هستند، نه یک فهرست تخت.
    'education': [
        ('کارگزینی هیئت علمی', '', []),
        ('حوزهٔ خدمات آموزشی', '', [
            ('مدیر آموزش', '', [
                ('کارشناسان آموزشی', '', []),
                ('امور فارغ‌التحصیلان', '', []),
                ('ادارهٔ امتحانات', '', []),
            ]),
        ]),
        ('گروه‌های آموزشی', 'academics:groups_list', [
            ('مدیریت گروه', '', [
                ('اعضای هیئت علمی', 'faculty:professors', []),
            ]),
        ]),
        ('تحصیلات تکمیلی', 'core:graduate_studies', [
            ('مدیر تحصیلات تکمیلی', 'core:graduate_manager', []),
        ]),
    ],
    'research': [
        ('مدیر پژوهشی', '', [
            ('انتشارات', '', []),
            ('کتابخانه', 'library:library', []),
            ('دفتر ارتباط با صنعت', '', []),
        ]),
        ('مدیر فناوری', '', [
            ('مرکز کامپیوتر', '', []),
        ]),
        ('دفتر همکاری‌های علمی و بین‌المللی', 'core:international_office', []),
        ('منابع پژوهشی', 'directory:resources', []),
    ],
    'admin_finance': [
        ('مدیر امور مالی و خزانه‌دار', '', [
            ('رئیس حسابداری', '', []),
            ('حسابدار', '', []),
            ('کاربردی', '', []),
            ('حسابدار اموال', '', []),
        ]),
        ('مدیر اداری و پشتیبانی', '', [
            ('کارگزینی و دبیرخانه', '', []),
            ('امور اداری و پشتیبانی', '', []),
        ]),
    ],
    'student': [
        ('مدیر دانشجویی', '', [
            ('ادارهٔ بهداشت و وام دانشجویی', '', []),
            ('ادارهٔ خوابگاه‌ها و نظام وظیفه', '', []),
            ('ادارهٔ تربیت بدنی', '', []),
        ]),
        ('مدیر فرهنگی', '', [
            ('ادارهٔ فرهنگی و فوق‌برنامه', '', []),
        ]),
        ('شورای فرهنگی', '', []),
        ('شورای دانشجویی', '', []),
        ('کمیته انضباطی', '', []),
    ],
    # چارت سازمانی معاونتی به این نام ندارد؛ سند اصلاحات موسسه آن را
    # به‌عنوان معاونت پنجم خواسته بود، پس در فهرست می‌ماند تا خودِ
    # موسسه تکلیفش را روشن کند.
    'construction': [],
}


def _url(name: str) -> str:
    """نشانی یک مسیر نام‌دار؛ اگر نبود، خالی به‌جای پرتاب خطا.

    یک مسیر حذف‌شده نباید کل نوار بالای سایت را از کار بیندازد.
    """
    try:
        return reverse(name)
    except NoReverseMatch:
        return ''


def _units(rows) -> list:
    """سه‌تایی‌های STATIC_UNITS را به دیکشنری‌های تودرتو تبدیل می‌کند."""
    built = []
    for title, name, kids in rows:
        built.append({
            'title': title,
            'url': _url(name) if name else '',
            'children': _units(kids),
        })
    return built


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

        children = _units(STATIC_UNITS.get(key, []))
        # گروه‌های دارای تحصیلات تکمیلی، زیر «تحصیلات تکمیلی»
        if key == 'education' and graduate_groups:
            for row in children:
                if row['title'] == 'تحصیلات تکمیلی':
                    row['children'] += [
                        {'title': group.name,
                         'url': group.get_absolute_url(),
                         'children': []}
                        for group in graduate_groups
                    ]
                    break
        # واحدهای ثبت‌شده در پنل — بدون صفحهٔ اختصاصی، پس بدون لینک
        if vice is not None:
            children += [
                {'title': unit.name, 'url': '', 'children': []}
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
