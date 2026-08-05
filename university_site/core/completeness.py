"""سنجهٔ کامل بودن صفحات معرفی — «این صفحه چقدر پر شده؟»

مسئله‌ای که حل می‌کند
─────────────────────
صفحات «درباره موسسه»، «حوزه ریاست» و «معاونت‌ها» ده‌ها فیلد اختیاری
دارند. اگر پر نشوند، صفحه بدون هیچ خطایی **خالی** رندر می‌شود: نه لاگی
می‌افتد، نه ادمین خبردار می‌شود. تنها وقتی معلوم می‌شود که بازدیدکننده
به یک صفحهٔ سفید برسد.

این ماژول برای هر رکورد حساب می‌کند چند درصد فیلدهای مهمش پر شده و
دقیقاً کدام‌ها جا مانده‌اند — تا ادمین در همان فهرست ببیند کجا کم است.

فیلدها وزن دارند: نبودِ نام رئیس با نبودِ فکس یکی نیست.
"""
from __future__ import annotations

# (نام فیلد, برچسب, وزن) — وزن ۳ یعنی «بدون این، صفحه بی‌معناست»
PROFILES = {
    'core.SiteSettings': [
        ('university_name_fa', 'نام موسسه', 3),
        ('about_short', 'معرفی کوتاه', 3),
        ('logo', 'لوگو', 2),
        ('address', 'نشانی', 3),
        ('phone', 'تلفن', 3),
        ('email', 'ایمیل', 2),
        ('postal_code', 'کد پستی', 1),
        ('established_year', 'سال تأسیس', 2),
        ('working_hours', 'ساعت کاری', 2),
        ('map_embed', 'نقشه', 1),
        ('instagram', 'اینستاگرام', 1),
        ('telegram', 'تلگرام', 1),
    ],
    'core.PresidencyOffice': [
        ('president_name', 'نام رئیس', 3),
        ('president_title', 'عنوان علمی رئیس', 2),
        ('president_photo', 'تصویر رئیس', 3),
        ('president_message', 'پیام رئیس', 3),
        ('president_bio', 'بیوگرافی رئیس', 2),
        ('president_education', 'سوابق تحصیلی', 2),
        ('president_resume', 'سوابق اجرایی', 2),
        ('president_email', 'ایمیل رئیس', 1),
        ('office_manager_name', 'مدیر دفتر', 2),
        ('office_duties', 'شرح وظایف دفتر', 2),
        ('office_phone', 'تلفن دفتر', 2),
        ('office_hours', 'ساعات کاری دفتر', 1),
    ],
    'core.VicePresidency': [
        ('full_name', 'نام معاون', 3),
        ('academic_rank', 'مرتبه علمی', 2),
        ('photo', 'تصویر', 3),
        ('description', 'معرفی معاونت', 3),
        ('duties', 'شرح وظایف', 3),
        ('goals', 'اهداف', 2),
        ('message', 'پیام معاون', 2),
        ('education', 'سوابق تحصیلی', 1),
        ('resume', 'سوابق اجرایی', 1),
        ('email', 'ایمیل', 1),
        ('phone', 'تلفن', 1),
    ],
    'core.PresidencyOfficeUnit': [
        ('title', 'عنوان واحد', 3),
        ('manager_name', 'نام مسئول', 3),
        ('duties', 'شرح وظایف', 3),
        ('phone', 'تلفن', 2),
        ('extension', 'شماره داخلی', 2),
        ('location', 'محل استقرار', 2),
        ('content', 'معرفی واحد', 2),
        ('manager_title', 'سمت مسئول', 1),
        ('email', 'ایمیل', 1),
        ('office_hours', 'ساعات مراجعه', 1),
        ('manager_photo', 'تصویر مسئول', 1),
    ],
    'core.OrganizationalChart': [
        ('name', 'نام واحد', 3),
        ('person_name', 'نام مسئول', 3),
        ('title', 'سمت', 2),
        ('person_photo', 'تصویر', 1),
        ('description', 'شرح وظایف', 2),
        ('person_phone', 'تلفن', 1),
        ('location', 'محل', 1),
    ],
    'core.BoardMember': [
        ('full_name', 'نام', 3),
        ('title', 'سمت', 3),
        ('photo', 'تصویر', 2),
        ('bio', 'بیوگرافی', 2),
        ('education', 'تحصیلات', 1),
    ],
    'core.InstitutionGoal': [
        ('title', 'عنوان هدف', 3),
        ('description', 'توضیح', 3),
    ],
}


# متنی که seed به‌عنوان جای‌نگهدار می‌گذارد؛ «پر» به حساب نمی‌آید.
# بدون این، دفتر ریاست ۱۰۰٪ گزارش می‌شد در حالی که نام رئیس هنوز
# «[نام را از پنل ادمین وارد کنید]» بود — یعنی سنجه دقیقاً همان چیزی
# را که باید پیدا کند، پنهان می‌کرد.
PLACEHOLDER_MARKS = ('[', ']', '…')


def _is_placeholder(text: str) -> bool:
    stripped = text.strip()
    return stripped.startswith('[') and stripped.endswith(']')


def _has_value(obj, name) -> bool:
    value = getattr(obj, name, None)
    if value is None:
        return False
    # FileField/ImageField خالی، مقدارِ falsy دارد ولی None نیست
    if hasattr(value, 'name'):
        return bool(value.name)
    if isinstance(value, str):
        return bool(value.strip()) and not _is_placeholder(value)
    return bool(value)


def spec_for(model) -> list:
    label = '%s.%s' % (model._meta.app_label, model._meta.object_name)
    spec = PROFILES.get(label, [])
    # فیلدهایی که روی این نسخه از مدل وجود ندارند نادیده گرفته شوند
    names = {f.name for f in model._meta.get_fields() if hasattr(f, 'attname')}
    return [row for row in spec if row[0] in names]


def evaluate(obj) -> dict:
    """{'percent': ۰..۱۰۰, 'missing': [برچسب‌های جامانده], 'critical': [...]}"""
    spec = spec_for(type(obj))
    if not spec:
        return {'percent': None, 'missing': [], 'critical': []}

    total = sum(weight for _n, _l, weight in spec)
    earned = 0
    missing, critical = [], []
    for name, label, weight in spec:
        if _has_value(obj, name):
            earned += weight
        else:
            missing.append(label)
            if weight >= 3:
                critical.append(label)

    percent = int(round(100 * earned / total)) if total else 0
    return {'percent': percent, 'missing': missing, 'critical': critical}
