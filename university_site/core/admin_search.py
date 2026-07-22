"""جستجوی سراسری ادمین + شمارنده‌های زنده داشبورد."""
from __future__ import annotations

from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.urls import NoReverseMatch, reverse
from django.utils.html import strip_tags
from django.views.decorators.http import require_GET

from core.templatetags.admin_dashboard import MODEL_HELP


def _model_admin_url(model):
    opts = model._meta
    try:
        return reverse(f'admin:{opts.app_label}_{opts.model_name}_changelist')
    except NoReverseMatch:
        return ''


def _model_add_url(model):
    opts = model._meta
    try:
        return reverse(f'admin:{opts.app_label}_{opts.model_name}_add')
    except NoReverseMatch:
        return ''


@staff_member_required
@require_GET
def admin_nav_search_index(request):
    """فهرست JSON همه مدل‌های قابل‌دسترس ادمین برای جستجوی نوار بالا."""
    items = []
    for model, model_admin in admin.site._registry.items():
        opts = model._meta
        if not model_admin.has_module_permission(request):
            continue
        if not model_admin.has_view_permission(request) and not model_admin.has_change_permission(request):
            continue
        url = _model_admin_url(model)
        if not url:
            continue
        key = opts.object_name.lower()
        name = str(opts.verbose_name_plural)
        app_name = str(opts.app_config.verbose_name) if opts.app_config else opts.app_label
        items.append({
            'name': name,
            'app': app_name,
            'app_label': opts.app_label,
            'key': key,
            'url': url,
            'add_url': _model_add_url(model) if model_admin.has_add_permission(request) else '',
            'help': MODEL_HELP.get(key, f'مدیریت {name}'),
            'filter': opts.app_label,
        })

    items.sort(key=lambda x: x['name'])
    return JsonResponse({'items': items, 'total': len(items)})


@staff_member_required
@require_GET
def admin_live_counters(request):
    """شمارنده‌های زنده برای داشبورد."""
    data = {
        'messages_new': 0,
        'applications_pending': 0,
        'messages_url': '',
        'applications_url': '',
    }
    try:
        from contact.models import ContactMessage
        data['messages_new'] = ContactMessage.objects.filter(status='new').count()
        data['messages_url'] = reverse('admin:contact_contactmessage_changelist') + '?status__exact=new'
    except Exception:
        pass
    try:
        from admissions.models import Application
        data['applications_pending'] = Application.objects.filter(
            status__in=['pending', 'reviewing', 'incomplete']
        ).count()
        data['applications_url'] = reverse('admin:admissions_application_changelist') + '?status__exact=pending'
    except Exception:
        pass
    return JsonResponse(data)


@require_GET
def public_live_search(request):
    """جستجوی زنده سایت عمومی — JSON برای باکس ذره‌بین."""
    q = (request.GET.get('q') or '').strip()
    filter_key = (request.GET.get('filter') or 'all').strip()
    if len(q) < 1:
        return JsonResponse({'results': [], 'query': q})

    def _norm(s: str) -> str:
        return (
            (s or '')
            .strip()
            .lower()
            .replace('ي', 'ی')
            .replace('ك', 'ک')
            .replace('\u200c', '')
            .replace('‌', '')
        )

    def _matches(query: str, *parts: str) -> bool:
        blob = _norm(' '.join(parts))
        nq = _norm(query)
        if not nq:
            return False
        if nq in blob:
            return True
        tokens = [t for t in nq.replace('-', ' ').split() if len(t) > 1]
        return bool(tokens) and all(t in blob for t in tokens)

    results = []

    # صفحات ثابت پرکاربرد
    static_pages = [
        {'title': 'صفحه اصلی', 'url': '/', 'type': 'page', 'filter': 'pages', 'hint': 'خانه سایت'},
        {'title': 'درباره موسسه', 'url': reverse('core:about'), 'type': 'page', 'filter': 'pages', 'hint': 'معرفی و تاریخچه'},
        {'title': 'اهداف موسسه', 'url': reverse('core:institution_goals'), 'type': 'page', 'filter': 'pages', 'hint': 'چشم‌انداز'},
        {'title': 'شهر بهنمیر', 'url': reverse('core:city_behnammir'), 'type': 'page', 'filter': 'pages', 'hint': 'آشنایی با شهر'},
        {'title': 'ریاست موسسه', 'url': reverse('core:presidency'), 'type': 'page', 'filter': 'pages', 'hint': 'حوزه ریاست'},
        {'title': 'دفتر ریاست', 'url': reverse('core:presidency_office'), 'type': 'page', 'filter': 'pages', 'hint': 'واحدهای دفتر'},
        {'title': 'تحصیلات تکمیلی', 'url': reverse('core:graduate_studies'), 'type': 'page', 'filter': 'pages', 'hint': 'کارشناسی ارشد'},
        {'title': 'خدمات الکترونیکی', 'url': reverse('core:eservices'), 'type': 'page', 'filter': 'pages', 'hint': 'لینک‌های سامانه‌ها'},
        {'title': 'گالری', 'url': reverse('core:gallery'), 'type': 'page', 'filter': 'pages', 'hint': 'تصاویر'},
        {'title': 'سوالات متداول', 'url': reverse('core:faq'), 'type': 'page', 'filter': 'pages', 'hint': 'FAQ'},
        {'title': 'شناسه واریز', 'url': reverse('core:payment_id'), 'type': 'page', 'filter': 'pages', 'hint': 'حساب بانکی'},
        {'title': 'آیین‌نامه‌ها و فرم‌ها', 'url': reverse('core:documents'), 'type': 'page', 'filter': 'pages', 'hint': 'دانلود فایل'},
        {'title': 'رویدادها', 'url': reverse('core:events'), 'type': 'page', 'filter': 'pages', 'hint': 'تقویم'},
        {'title': 'پذیرش', 'url': reverse('admissions:admissions'), 'type': 'page', 'filter': 'pages', 'hint': 'ثبت‌نام آنلاین'},
        {'title': 'ثبت‌نام آنلاین', 'url': reverse('admissions:apply_otp_send'), 'type': 'page', 'filter': 'pages', 'hint': 'تأیید موبایل پذیرش'},
        {'title': 'تماس با ما', 'url': reverse('contact:contact'), 'type': 'page', 'filter': 'pages', 'hint': 'پیام و آدرس'},
        {'title': 'اخبار', 'url': reverse('news:list'), 'type': 'page', 'filter': 'pages', 'hint': 'فهرست اخبار'},
        {'title': 'اساتید', 'url': reverse('faculty:list'), 'type': 'page', 'filter': 'pages', 'hint': 'هیأت علمی'},
        {'title': 'کتابخانه', 'url': reverse('library:library'), 'type': 'page', 'filter': 'pages', 'hint': 'بانک علمی'},
    ]
    for page in static_pages:
        if _matches(q, page['title'], page['hint'], page.get('type', '')):
            results.append(page)

    try:
        from news.models import News
        for n in News.objects.filter(is_published=True, title__icontains=q)[:8]:
            try:
                url = reverse('news:detail', kwargs={'slug': n.slug}) if getattr(n, 'slug', None) else reverse('news:list')
            except Exception:
                url = reverse('news:list')
            results.append({
                'title': n.title,
                'url': url,
                'type': 'news',
                'filter': 'news',
                'hint': 'خبر / اطلاعیه',
            })
    except Exception:
        pass

    try:
        from faculty.models import Professor
        from django.db.models import Q
        qs = Professor.objects.filter(is_active=True).filter(
            Q(first_name__icontains=q) | Q(last_name__icontains=q)
        )[:8]
        for p in qs:
            try:
                slug = getattr(p, 'slug', None) or p.pk
                url = reverse('faculty:professor_detail', args=[slug])
            except Exception:
                url = reverse('faculty:list')
            results.append({
                'title': f'{p.first_name} {p.last_name}'.strip(),
                'url': url,
                'type': 'professor',
                'filter': 'faculty',
                'hint': 'عضو هیأت علمی',
            })
    except Exception:
        pass

    try:
        from academics.models import Major
        for m in Major.objects.filter(is_active=True, name__icontains=q)[:8]:
            try:
                slug = getattr(m, 'slug', None) or m.pk
                url = reverse('academics:major_detail', args=[slug])
            except Exception:
                url = reverse('academics:majors')
            results.append({
                'title': m.name,
                'url': url,
                'type': 'major',
                'filter': 'academics',
                'hint': 'رشته تحصیلی',
            })
    except Exception:
        pass

    try:
        from core.models import FAQ, Event
        for f in FAQ.objects.filter(is_active=True, question__icontains=q)[:5]:
            results.append({
                'title': strip_tags(f.question)[:80],
                'url': reverse('core:faq'),
                'type': 'faq',
                'filter': 'pages',
                'hint': 'سوال متداول',
            })
        for e in Event.objects.filter(is_active=True, title__icontains=q)[:5]:
            results.append({
                'title': e.title,
                'url': reverse('core:events'),
                'type': 'event',
                'filter': 'pages',
                'hint': 'رویداد',
            })
    except Exception:
        pass

    if filter_key and filter_key != 'all':
        results = [r for r in results if r.get('filter') == filter_key]

    # de-dupe by url+title
    seen = set()
    unique = []
    for r in results:
        k = (r.get('url'), r.get('title'))
        if k in seen:
            continue
        seen.add(k)
        unique.append(r)

    return JsonResponse({'results': unique[:20], 'query': q})
