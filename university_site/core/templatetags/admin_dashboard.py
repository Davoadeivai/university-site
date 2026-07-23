"""ابزارهای داشبورد ادمین: فهرست الفبایی و راهنمای کوتاه هر بخش."""
from __future__ import annotations

from collections import defaultdict
from django import template

register = template.Library()

# ترتیب حروف فارسی برای فهرست الفبایی
_PERSIAN_ALPHA = list('آابپتثجچحخدذرزژسشصضطظعغفقکگلمنوهی')
_LETTER_RANK = {ch: i for i, ch in enumerate(_PERSIAN_ALPHA)}

# راهنمای کوتاه برای ادمین (کلید: object_name مدل به صورت lowercase)
MODEL_HELP = {
    'sitesettings': 'نام موسسه، لوگو، تماس، آمار صفحه اصلی، لینک‌های خدمات الکترونیکی',
    'slider': 'اسلایدهای بنر صفحه اصلی سایت',
    'quicklink': 'لینک‌های سریع صفحه اصلی و فوتر',
    'event': 'رویدادها و تقویم عمومی سایت',
    'faq': 'پرسش‌های متداول',
    'institutiongoal': 'اهداف و مأموریت موسسه',
    'boardmember': 'اعضای هیأت امناء / هیأت رئیسه',
    'cityinfo': 'معرفی شهر بهنمیر',
    'cityattraction': 'جاذبه‌های گردشگری بهنمیر',
    'presidencyoffice': 'دفتر ریاست و شرح وظایف',
    'officeunit': 'واحدهای دفتر ریاست (دبیرخانه‌ها)',
    'deputyvice': 'معاونت‌ها',
    'internationaloffice': 'دفتر امور بین‌الملل',
    'internationalactivity': 'فعالیت‌های بین‌المللی',
    'publicrelations': 'روابط عمومی',
    'pressrelease': 'بیانیه‌ها و اخبار روابط عمومی',
    'securityoffice': 'حراست',
    'vicepresidency': 'معاونت‌های سازمانی',
    'viceunit': 'واحدهای زیرمجموعه معاونت‌ها',
    'viceachievement': 'دستاوردهای معاونت‌ها',
    'organizationalchart': 'چارت سازمانی',
    'bankaccount': 'شماره حساب‌های بانکی موسسه',
    'paymentidentifier': 'شناسه‌های واریز',
    'downloadabledocument': 'فرم‌ها و فایل‌های قابل دانلود',
    'graduatestudiesinfo': 'اطلاعات تحصیلات تکمیلی و مدیر بخش',
    'graduatemajor': 'رشته‌های کارشناسی ارشد',
    'graduatedocument': 'آیین‌نامه‌ها و فرم‌های تحصیلات تکمیلی',
    'admissioninfo': 'متن و شرایط پذیرش',
    'application': 'درخواست‌های ثبت‌نام آنلاین دانشجویان',
    'tuitionstructure': 'شهریه رشته‌ها',
    'tuitiondiscount': 'تخفیف‌های شهریه',
    'studentpayment': 'پرداخت‌های دانشجویی',
    'admissionotp': 'کدهای تأیید پیامکی پذیرش',
    'department': 'دانشکده‌ها / گروه‌های اصلی',
    'academicgroup': 'گروه‌های آموزشی',
    'major': 'رشته‌های تحصیلی',
    'course': 'دروس',
    'academiccalendar': 'تقویم آموزشی',
    'laboratory': 'آزمایشگاه‌ها',
    'professor': 'اعضای هیأت علمی',
    'publication': 'مقالات و آثار اساتید',
    'category': 'دسته‌بندی اخبار',
    'news': 'اخبار و اطلاعیه‌های عمومی سایت',
    'gallery': 'گالری تصاویر',
    'book': 'کتاب‌های کتابخانه',
    'article': 'مقالات کتابخانه / بانک علمی',
    'librarymembership': 'عضویت کتابخانه',
    'researchproject': 'طرح‌های پژوهشی',
    'journal': 'نشریات علمی',
    'thesis': 'پایان‌نامه‌ها',
    'conference': 'همایش‌ها',
    'industrypartnership': 'همکاری با صنعت',
    'semester': 'نیمسال‌های تحصیلی',
    'enrollment': 'انتخاب واحد',
    'teachingassignment': 'تخصیص تدریس',
    'studentrequest': 'درخواست‌های دانشجویی داشبورد',
    'payment': 'پرداخت‌های داشبورد',
    'examschedule': 'برنامه امتحانات',
    'assignment': 'تکالیف',
    'assignmentsubmission': 'تحویل تکالیف',
    'attendance': 'حضور و غیاب',
    'userprofile': 'پروفایل کاربران (نقش، کد ملی، رشته)',
    'announcement': 'اطلاعیه‌های داخلی برای کاربران',
    'otpcode': 'کدهای یک‌بارمصرف ورود',
    'contactmessage': 'پیام‌های فرم تماس با ما',
    'alumni': 'فارغ‌التحصیلان',
    'user': 'حساب‌های کاربری سیستم',
    'group': 'گروه‌های دسترسی',
    'logentry': 'لاگ فعالیت‌های ادمین',
}

# میانبرهای پیشنهادی داشبورد (object_name lowercase)
QUICK_KEYS = (
    'sitesettings',
    'application',
    'contactmessage',
    'news',
    'gallery',
    'announcement',
    'bankaccount',
    'graduatestudiesinfo',
    'presidencyoffice',
    'professor',
)


def _first_letter(name: str) -> str:
    name = (name or '').strip()
    if not name:
        return '#'
    ch = name[0]
    if ch == 'ا':
        return 'ا'
    if ch in _LETTER_RANK:
        return ch
    # ارقام / انگلیسی
    if ch.isascii() and ch.isalpha():
        return ch.upper()
    if ch.isdigit():
        return '#'
    return ch


def _letter_sort_key(letter: str):
    if letter in _LETTER_RANK:
        return (0, _LETTER_RANK[letter])
    if letter == '#':
        return (2, 0)
    return (1, letter)


def _model_key(model: dict) -> str:
    return (model.get('object_name') or model.get('name') or '').lower()


def _flatten_models(dashboard_list) -> list[dict]:
    items = []
    for app in dashboard_list or []:
        app_name = app.get('name') or ''
        app_label = app.get('app_label') or ''
        for model in app.get('models') or []:
            key = _model_key(model)
            name = model.get('name') or key
            url = model.get('url') or model.get('admin_url') or ''
            items.append({
                'name': name,
                'app_name': app_name,
                'app_label': app_label,
                'object_name': model.get('object_name') or '',
                'url': url,
                'add_url': model.get('add_url') or '',
                'view_only': bool(model.get('view_only')),
                'custom': bool(model.get('custom')),
                'help': MODEL_HELP.get(key, f'مدیریت بخش «{name}» در {app_name}'),
                'letter': _first_letter(name),
                'key': key,
            })
    items.sort(key=lambda m: (m['name'], m['app_name']))
    return items


def _live_counters():
    counters = {
        'messages_new': 0,
        'applications_pending': 0,
        'messages_url': '',
        'applications_url': '',
    }
    try:
        from django.urls import reverse
        from contact.models import ContactMessage
        from admissions.models import Application

        counters['messages_new'] = ContactMessage.objects.filter(status='new').count()
        counters['messages_url'] = reverse('admin:contact_contactmessage_changelist') + '?status__exact=new'
        counters['applications_pending'] = Application.objects.filter(
            status__in=['pending', 'reviewing', 'incomplete']
        ).count()
        counters['applications_url'] = (
            reverse('admin:admissions_application_changelist') + '?status__exact=pending'
        )
    except Exception:
        pass
    return counters


@register.simple_tag
def admin_dashboard_catalog(dashboard_list):
    """
    خروجی:
    - items: همه مدل‌ها (مرتب الفبایی)
    - alpha_groups: [(letter, [models...]), ...]
    - letters: حروف موجود برای پرش سریع
    - quick: میانبرهای پرتکرار
    - counters: شمارنده‌های زنده
    - apps: لیست گروه‌ها برای فیلتر
    """
    items = _flatten_models(dashboard_list)
    grouped = defaultdict(list)
    for item in items:
        grouped[item['letter']].append(item)

    letters = sorted(grouped.keys(), key=_letter_sort_key)
    alpha_groups = [(letter, grouped[letter]) for letter in letters]

    by_key = {m['key']: m for m in items}
    quick = [by_key[k] for k in QUICK_KEYS if k in by_key]

    apps = []
    seen_apps = set()
    for item in items:
        label = item['app_name']
        if label and label not in seen_apps:
            seen_apps.add(label)
            apps.append(label)

    mid = (len(items) + 1) // 2
    left_col = items[:mid]
    right_col = items[mid:]

    return {
        'items': items,
        'left_col': left_col,
        'right_col': right_col,
        'alpha_groups': alpha_groups,
        'letters': letters,
        'quick': quick,
        'total': len(items),
        'counters': _live_counters(),
        'apps': apps,
    }
