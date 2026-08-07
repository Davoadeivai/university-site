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


# ─────────────────────────────────────────────────────────────────────
#  صف کار ادمین — تنها منبع حقیقت برای شمارنده‌ها
#  (هم رندر سمت سرور در templatetag و هم پولینگ JSON از اینجا می‌خوانند)
# ─────────────────────────────────────────────────────────────────────

def _queue_specs():
    """هر ورودی: (کلید, برچسب, ساخت‌کننده queryset, آدرس، آیکون، فوریت)"""
    from accounts.models import UserProfile  # noqa: F401  (بارگذاری تنبل اپ‌ها)

    def _url(viewname, query=''):
        try:
            return reverse(viewname) + query
        except NoReverseMatch:
            return ''

    specs = []

    try:
        from admissions.models import Application
        specs.append((
            'applications_pending', 'پذیرش در انتظار بررسی',
            lambda: Application.objects.filter(
                status__in=['pending', 'reviewing', 'incomplete']).count(),
            _url('admin:admissions_application_changelist', '?status__exact=pending'),
            'fa-user-graduate', True,
        ))
    except Exception:
        pass

    try:
        from contact.models import ContactMessage
        specs.append((
            'messages_new', 'پیام خوانده‌نشده',
            lambda: ContactMessage.objects.filter(status='new').count(),
            _url('admin:contact_contactmessage_changelist', '?status__exact=new'),
            'fa-envelope', True,
        ))
    except Exception:
        pass

    try:
        from dashboard.models import Payment
        specs.append((
            'payments_review', 'پرداخت آفلاین منتظر تأیید',
            lambda: Payment.objects.filter(status='review').count(),
            _url('admin:dashboard_payment_changelist', '?status__exact=review'),
            'fa-money-check-alt', True,
        ))
    except Exception:
        pass

    try:
        from dashboard.models import StudentDiscountClaim
        specs.append((
            'discounts_pending', 'درخواست تخفیف معلق',
            lambda: StudentDiscountClaim.objects.filter(status='pending').count(),
            _url('admin:dashboard_studentdiscountclaim_changelist', '?status__exact=pending'),
            'fa-percent', False,
        ))
    except Exception:
        pass

    try:
        from dashboard.models import StudentLifecycleRequest
        specs.append((
            'lifecycle_pending', 'درخواست وضعیت تحصیلی',
            lambda: StudentLifecycleRequest.objects.filter(
                status__in=['submitted', 'under_review']).count(),
            _url('admin:dashboard_studentlifecyclerequest_changelist', '?status__exact=submitted'),
            'fa-file-signature', False,
        ))
    except Exception:
        pass

    try:
        from dashboard.models import StudentClearance
        specs.append((
            'clearance_open', 'تسویه ناتمام',
            lambda: StudentClearance.objects.exclude(status='completed').count(),
            _url('admin:dashboard_studentclearance_changelist', ''),
            'fa-clipboard-check', False,
        ))
    except Exception:
        pass

    return specs


def build_work_queue() -> list[dict]:
    """صف کارهای معطل ادمین — فقط مواردی که شمارش‌شان > ۰ نیست هم برگردانده می‌شوند."""
    out = []
    for key, label, counter, url, icon, urgent in _queue_specs():
        try:
            count = counter()
        except Exception:
            continue
        out.append({
            'key': key, 'label': label, 'count': count,
            'url': url, 'icon': icon, 'urgent': urgent,
        })
    return out


@staff_member_required
@require_GET
def admin_live_counters(request):
    """شمارنده‌های زنده برای داشبورد (پولینگ صفحه اول)."""
    queue = build_work_queue()
    data = {item['key']: item['count'] for item in queue}
    data['queue'] = queue
    data['total_pending'] = sum(i['count'] for i in queue)
    # سازگاری با نسخه قبلی قالب
    for item in queue:
        if item['key'] == 'messages_new':
            data['messages_url'] = item['url']
        elif item['key'] == 'applications_pending':
            data['applications_url'] = item['url']
    return JsonResponse(data)


@require_GET
def public_live_search(request):
    """جستجوی زندهٔ سایت — JSON برای باکس ذره‌بین.

    هدف: هرچه در سایت هست با تایپ بخشی از نامش پیدا شود؛ نه فقط صفحات
    ثابت و اخبار، بلکه فرم‌ها، رشته‌ها، دروس، کتاب‌ها، رویدادها و … .

    نکتهٔ فارسی: کاربر ممکن است «ي» و «ك» عربی یا نیم‌فاصله بنویسد در
    حالی که متن پایگاه داده شکل دیگری دارد. کوئری به چند شکل تبدیل و
    همه با OR جستجو می‌شوند — وگرنه «پايان نامه» هرگز «پایان‌نامه» را
    پیدا نمی‌کرد.
    """
    from core.sms import check_rate_limit

    q = (request.GET.get('q') or '').strip()
    filter_key = (request.GET.get('filter') or 'all').strip()
    if len(q) < 1:
        return JsonResponse({'results': [], 'query': q})

    # اندپوینت عمومی و بدون احراز هویت است و هر بار چند کوئری icontains
    # می‌زند؛ بدون سقف، یک اسکریپت ساده می‌تواند دیتابیس را مشغول کند.
    # دیبونس سمت کلاینت محافظت نیست.
    # سقف صریح و بالا، چون اینجا IP تنها کلید ممکن است و پشت یک IP
    # اپراتور موبایل ده‌ها دانشجو می‌نشینند. ۹۰ در دقیقه برای یک نفر
    # زیاد است ولی برای یک اپراتور کم؛ ۶۰۰ هر دو را می‌پوشاند و
    # همچنان جلوی اسکریپت را می‌گیرد.
    allowed, _msg = check_rate_limit(
        request, 'live_search', limit=90, window=60, ip_limit=600)
    if not allowed:
        return JsonResponse({'results': [], 'query': q, 'throttled': True}, status=429)

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

    def _variants(query: str) -> list:
        """شکل‌های محتملِ همان عبارت، برای جستجوی پایگاه داده."""
        base = query.strip()
        forms = {
            base,
            base.replace('ي', 'ی').replace('ك', 'ک'),
            base.replace('ی', 'ي').replace('ک', 'ك'),
            base.replace('‌', ' '),
            base.replace(' ', '‌'),
            base.replace('‌', ''),
        }
        return [f for f in forms if f]

    def _q_for(fields, query: str):
        """Q ترکیبی: هر فیلد × هر شکل عبارت."""
        from django.db.models import Q
        cond = Q()
        for field in fields:
            for form in _variants(query):
                cond |= Q(**{'%s__icontains' % field: form})
        return cond

    results = []

    def collect(model, fields, url_fn, type_key, group, hint,
                limit=6, only=None, label=None):
        """جستجوی یک مدل و افزودن نتایج.

        هر مدلی که آدرسش برقرار نشود بی‌سروصدا رد می‌شود — یک اپ ناقص
        نباید کل جستجو را بشکند.
        """
        try:
            qs = model.objects.all()
            if only:
                qs = qs.filter(**only)
            for obj in qs.filter(_q_for(fields, q))[:limit]:
                try:
                    url = url_fn(obj)
                except Exception:
                    continue
                title = (label(obj) if label else str(obj)) or ''
                results.append({
                    'title': title[:90],
                    'url': url,
                    'type': type_key,
                    'filter': group,
                    'hint': hint,
                })
        except Exception:
            pass

    # صفحات ثابت پرکاربرد
    static_pages = [
        {'title': 'صفحه اصلی', 'url': '/', 'type': 'page', 'filter': 'pages', 'hint': 'خانه سایت'},
        {'title': 'درباره موسسه', 'url': reverse('core:about'), 'type': 'page', 'filter': 'pages', 'hint': 'معرفی و تاریخچه'},
        {'title': 'اهداف موسسه', 'url': reverse('core:institution_goals'), 'type': 'page', 'filter': 'pages', 'hint': 'چشم‌انداز'},
        {'title': 'شهر بابلسر', 'url': reverse('core:city_behnammir'), 'type': 'page', 'filter': 'pages', 'hint': 'آشنایی با شهر'},
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

    # ── محتوایی که تا پیش از این در جستجو دیده نمی‌شد ──────────────────
    # فرم‌ها و آیین‌نامه‌ها پرجستجوترین چیز سایت‌اند و اصلاً پوشش نداشتند.
    try:
        from core.models import (
            DownloadableDocument, CityAttraction, QuickLink, BoardMember,
            DeputyVice, PressRelease,
        )
        collect(
            DownloadableDocument, ['title', 'description'],
            lambda d: reverse('core:document_detail', args=[d.pk]),
            'document', 'docs', 'فرم / آیین‌نامه', limit=8,
            only={'is_active': True}, label=lambda d: d.title,
        )
        collect(
            QuickLink, ['title'],
            lambda l: l.url or reverse('core:eservices'),
            'link', 'pages', 'دسترسی سریع', limit=4,
            only={'is_active': True}, label=lambda l: l.title,
        )
        # نام فیلدها باید با مدل بخواند. تا پیش از این `name`/`position`
        # و `name`/`title` صدا زده می‌شد که در هیچ‌کدام از این دو مدل
        # وجود ندارد؛ `collect` خطا را می‌بلعید و این دو دسته هیچ‌وقت
        # در نتایج جست‌وجو دیده نمی‌شدند.
        collect(
            BoardMember, ['full_name', 'title'],
            lambda m: reverse('core:board_trustees') if m.board_type == 'trustee'
            else reverse('core:board_founders'),
            'person', 'pages', 'هیأت موسس / امنا', limit=4,
            only={'is_active': True},
            label=lambda m: '%s — %s' % (m.full_name, m.title) if m.title else m.full_name,
        )
        collect(
            DeputyVice, ['full_name', 'academic_rank'],
            lambda d: reverse('core:deputies'),
            'person', 'pages', 'معاونت', limit=4,
            label=lambda d: '%s — %s' % (d.full_name, d.get_vice_type_display()),
        )
        collect(
            PressRelease, ['title'],
            lambda p: reverse('core:public_relations'),
            'news', 'news', 'اطلاعیه روابط عمومی', limit=4,
            only={'is_active': True}, label=lambda p: p.title,
        )
        collect(
            CityAttraction, ['name', 'description'],
            lambda a: reverse('core:city_behnammir'),
            'page', 'pages', 'جاذبهٔ شهر', limit=3,
            label=lambda a: a.name,
        )
    except Exception:
        pass

    # ── بانک اطلاعات موسسه ────────────────────────────────────────────
    # جست‌وجوی «۱۱۵» یا «مدیر پژوهشی» باید مستقیم به دفترچهٔ تلفن برسد،
    # و جست‌وجوی نام یک رشته به سرفصل مصوبش.
    try:
        from directory.models import (
            CurriculumDocument, DirectoryPerson, ExternalResource,
        )
        collect(
            DirectoryPerson, ['full_name', 'position', 'field_of_study', 'extension'],
            lambda p: reverse('directory:staff') if p.category == 'staff'
            else reverse('directory:people'),
            'person', 'pages', 'افراد موسسه', limit=6,
            only={'is_active': True},
            label=lambda p: '%s — %s' % (
                p.display_name, p.position or p.field_of_study or p.get_category_display()),
        )
        collect(
            CurriculumDocument, ['title', 'note'],
            lambda d: reverse('directory:curriculum_download', args=[d.pk]),
            'document', 'docs', 'سرفصل مصوب', limit=6,
            only={'is_active': True},
            label=lambda d: '%s (%s)' % (d.title, d.get_level_display()),
        )
        collect(
            ExternalResource, ['title', 'description'],
            lambda r: reverse('directory:resources'),
            'link', 'pages', 'پایگاه پژوهشی', limit=3,
            only={'is_active': True}, label=lambda r: r.title,
        )
    except Exception:
        pass

    try:
        from academics.models import Course, Department, AcademicGroup, Laboratory
        collect(
            Course, ['name', 'code'],
            lambda c: reverse('academics:majors'),
            'course', 'academics', 'درس', limit=6,
            label=lambda c: c.name,
        )
        collect(
            Department, ['name'],
            lambda d: reverse('academics:department_detail', args=[d.slug or d.pk]),
            'department', 'academics', 'دانشکده', limit=4,
            only={'is_active': True}, label=lambda d: d.name,
        )
        collect(
            AcademicGroup, ['name'],
            lambda g: reverse('academics:group_detail', args=[g.slug or g.pk]),
            'group', 'academics', 'گروه آموزشی', limit=4,
            only={'is_active': True}, label=lambda g: g.name,
        )
        collect(
            Laboratory, ['name', 'description'],
            lambda l: reverse('academics:laboratories'),
            'lab', 'academics', 'آزمایشگاه', limit=3,
            label=lambda l: l.name,
        )
    except Exception:
        pass

    try:
        from library.models import Book, Article
        collect(
            Book, ['title', 'author'],
            lambda b: reverse('library:book_detail', args=[b.pk]),
            'book', 'library', 'کتاب', limit=6,
            label=lambda b: b.title,
        )
        collect(
            Article, ['title', 'author'],
            lambda a: reverse('library:library'),
            'article', 'library', 'مقاله', limit=4,
            label=lambda a: a.title,
        )
    except Exception:
        pass

    try:
        from research.models import Journal, Conference, ResearchProject, Thesis
        collect(
            Journal, ['title'], lambda j: reverse('research:journals'),
            'journal', 'research', 'مجله علمی', limit=4, label=lambda j: j.title,
        )
        collect(
            Conference, ['title'], lambda c: reverse('research:conferences'),
            'conference', 'research', 'همایش', limit=4, label=lambda c: c.title,
        )
        collect(
            ResearchProject, ['title'], lambda p: reverse('research:projects'),
            'project', 'research', 'طرح پژوهشی', limit=4, label=lambda p: p.title,
        )
        collect(
            Thesis, ['title', 'author'], lambda t: reverse('research:theses'),
            'thesis', 'research', 'پایان‌نامه', limit=4, label=lambda t: t.title,
        )
    except Exception:
        pass

    try:
        from news.models import Gallery
        from contact.models import Alumni
        collect(
            Gallery, ['title'], lambda g: reverse('core:gallery'),
            'gallery', 'pages', 'تصویر گالری', limit=3, label=lambda g: g.title,
        )
        collect(
            Alumni, ['name', 'position'], lambda a: reverse('core:home'),
            'person', 'pages', 'فارغ‌التحصیل', limit=3, label=lambda a: a.name,
        )
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
