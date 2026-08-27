from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count
from django.utils import timezone
from django.db.models import Q

from core.models import (
    MAX_HOME_SLIDES, SiteSettings, Slider, QuickLink, Event, FAQ, InstitutionGoal, BoardMember,
    CityInfo, CityAttraction,
    PresidencyOffice, PresidencyOfficeUnit, DeputyVice,
    InternationalOffice, InternationalActivity,
    PublicRelations, PressRelease,
    SecurityOffice,
    VicePresidency, ViceUnit, ViceAchievement,
    OrganizationalChart,
    BankAccount, PaymentIdentifier, DownloadableDocument,
    GraduateStudiesInfo,
    HomeFeature,
)
from core.academic_timeline import build_timeline
from news.models import News, Category, Gallery
from academics.models import Department, Major, AcademicCalendar
from faculty.models import Professor
from contact.models import Alumni
from research.models import ResearchProject, Conference


def home(request):
    """صفحه اصلی یکپارچه سایت (جایگزین landing + home قبلی)."""
    # site_settings از global_context می‌آید؛ کوئری تکراری حذف شد
    # چند اسلاید نمایش داده شود را مدیر از پنل تعیین می‌کند. پیش از
    # این عدد ۵ همین‌جا نوشته شده بود و اسلاید ششم به بعد بی‌صدا
    # کنار گذاشته می‌شد — مدیر آپلود می‌کرد و هیچ‌وقت نمی‌دیدشان.
    settings_row = SiteSettings.objects.first()
    limit = getattr(settings_row, 'home_slider_count', None) or MAX_HOME_SLIDES
    sliders = list(
        Slider.objects.filter(is_active=True)
        .order_by('order')[:min(limit, MAX_HOME_SLIDES)]
    )
    quick_links = QuickLink.objects.filter(is_active=True, category='home')[:8]
    if not quick_links.exists():
        quick_links = QuickLink.objects.filter(is_active=True, category='eservice')[:8]

    published = News.objects.filter(is_published=True).select_related('category')
    featured_news = published.filter(is_featured=True)[:3]
    latest_news = published[:6]
    announcements = list(published.filter(news_type='announcement')[:8])
    news_events = list(published.order_by('-published_at')[:8])
    # تب‌ها از همان دو لیست — بدون کوئری جدا برای هر دسته
    announcement_tabs = [
        ('all', 'همه', announcements),
        ('news_events', 'اخبار و رویدادها', news_events),
        (
            'academic',
            'آموزش',
            [n for n in announcements if getattr(getattr(n, 'category', None), 'category_type', None) == 'academic'][:8],
        ),
        (
            'cultural',
            'دانشجویی و فرهنگی',
            [n for n in announcements if getattr(getattr(n, 'category', None), 'category_type', None) == 'cultural'][:8],
        ),
        (
            'administrative',
            'اداری و مالی',
            [n for n in announcements if getattr(getattr(n, 'category', None), 'category_type', None) == 'administrative'][:8],
        ),
        (
            'research',
            'پژوهشی و فناوری',
            [n for n in announcements if getattr(getattr(n, 'category', None), 'category_type', None) == 'research'][:8],
        ),
    ]
    upcoming_events = Event.objects.filter(
        is_active=True, date__gte=timezone.now().date()
    ).order_by('date')[:4]
    # بدون ترتیب صریح، به ترتیب پیش‌فرض مدل تکیه می‌کرد و با صفحهٔ
    # دانشکده‌ها هم‌خوان نبود؛ حالا هر دو یک ترتیب دارند.
    #
    # سقف هم برداشته شد: با ۶ تا، دانشکدهٔ هفتم در منو می‌آمد و در
    # صفحهٔ اصلی بی‌صدا غایب می‌شد — همان دامی که اسلاید ششم در آن
    # افتاده بود.
    departments = Department.objects.filter(is_active=True).order_by(
        'order', 'name')
    calendar_items = AcademicCalendar.objects.filter(
        start_date__gte=timezone.now().date()
    ).order_by('start_date')[:5]
    # اساتیدی که صریحاً برای صفحهٔ اصلی علامت خورده‌اند؛ اگر هیچ‌کدام
    # علامت نخورده باشد، به ترتیب نمایش برمی‌گردیم تا بخش خالی نماند
    featured_professors = list(
        Professor.objects.filter(is_active=True, is_featured=True)
        .select_related('department').order_by('order')[:4]
    )
    if not featured_professors:
        featured_professors = list(
            Professor.objects.filter(is_active=True)
            .select_related('department').order_by('order')[:4]
        )
    faqs = FAQ.objects.filter(is_active=True)[:6]
    gallery_images = Gallery.objects.filter(is_active=True, media_type='image')[:8]
    alumni = Alumni.objects.filter(is_featured=True)[:4]
    bank_accounts = BankAccount.objects.filter(is_active=True)[:3]

    context = {
        'sliders': sliders,
        'quick_links': quick_links,
        'featured_news': featured_news,
        'latest_news': latest_news,
        'announcements': announcements,
        'announcement_tabs': announcement_tabs,
        'upcoming_events': upcoming_events,
        'departments': departments,
        'calendar_items': calendar_items,
        'timeline': build_timeline(),
        'home_features': HomeFeature.objects.filter(is_active=True),
        'featured_professors': featured_professors,
        'faqs': faqs,
        'gallery_images': gallery_images,
        'alumni': alumni,
        'bank_accounts': bank_accounts,
        'page_title': 'صفحه اصلی',
    }
    return render(request, 'core/home.html', context)


def about(request):
    settings = SiteSettings.objects.first()
    org_chart = OrganizationalChart.objects.filter(is_active=True, parent__isnull=True).order_by('order')
    context = {
        'settings': settings,
        'org_chart': org_chart,
        'page_title': 'معرفی دانشگاه',
    }
    return render(request, 'core/about.html', context)


def city_behnammir(request):
    city_info = CityInfo.objects.filter(is_active=True).order_by('order')
    attractions = CityAttraction.objects.filter(is_active=True).order_by('order')
    categories = (
        attractions.exclude(category='')
        .values_list('category', flat=True)
        .distinct()
    )
    context = {
        'page_title': 'آشنایی با شهر بابلسر',
        'city_info': city_info,
        'attractions': attractions,
        'categories': categories,
    }
    return render(request, 'core/city_behnammir.html', context)


def institution_goals(request):
    goals = InstitutionGoal.objects.filter(is_active=True)
    strategic = goals.filter(goal_type='strategic')
    educational = goals.filter(goal_type='educational')
    research = goals.filter(goal_type='research')
    cultural = goals.filter(goal_type='cultural')
    social = goals.filter(goal_type='social')
    context = {
        'goals': goals,
        'strategic': strategic,
        'educational': educational,
        'research': research,
        'cultural': cultural,
        'social': social,
        'page_title': 'اهداف موسسه',
    }
    return render(request, 'core/institution_goals.html', context)


def board_founders(request):
    founders = BoardMember.objects.filter(is_active=True, board_type='founder')
    context = {
        'founders': founders,
        'page_title': 'هیات موسس دانشگاه',
    }
    return render(request, 'core/board_founders.html', context)


def board_trustees(request):
    trustees = BoardMember.objects.filter(is_active=True, board_type='trustee')
    context = {
        'trustees': trustees,
        'page_title': 'هیات امناء دانشگاه',
    }
    return render(request, 'core/board_trustees.html', context)


def search(request):
    query = request.GET.get('q', '')
    results = []
    if query:
        news_results = News.objects.filter(
            is_published=True, title__icontains=query
        )[:5]
        professor_results = Professor.objects.filter(
            is_active=True
        ).filter(
            first_name__icontains=query
        ) | Professor.objects.filter(last_name__icontains=query)
        professor_results = professor_results[:5]
        major_results = Major.objects.filter(
            is_active=True, name__icontains=query
        )[:5]
        results = {
            'news': news_results,
            'professors': professor_results,
            'majors': major_results,
        }
    context = {
        'query': query,
        'results': results,
        'page_title': f'جستجو: {query}',
    }
    return render(request, 'core/search.html', context)


def faq_view(request):
    faqs = FAQ.objects.filter(is_active=True)
    general_faqs = faqs.filter(category='general')
    admission_faqs = faqs.filter(category='admission')
    academic_faqs = faqs.filter(category='academic')
    financial_faqs = faqs.filter(category='financial')
    context = {
        'faqs': faqs,
        'general_faqs': general_faqs,
        'admission_faqs': admission_faqs,
        'academic_faqs': academic_faqs,
        'financial_faqs': financial_faqs,
        'page_title': 'سوالات متداول',
    }
    return render(request, 'core/faq.html', context)


def eservices(request):
    settings = SiteSettings.objects.first()
    eservice_links = QuickLink.objects.filter(is_active=True, category='eservice')
    context = {
        'page_title': 'خدمات الکترونیکی',
        'settings': settings,
        'eservice_links': eservice_links,
    }
    return render(request, 'core/eservices.html', context)


def payment_id(request):
    """شماره حساب و دریافت شناسه واریز شهریه"""
    accounts = BankAccount.objects.filter(is_active=True)
    result = None
    query = ''
    searched = False
    if request.method == 'POST':
        searched = True
        query = (request.POST.get('query') or '').strip()
        from core.sms import check_rate_limit
        allowed, rl_msg = check_rate_limit(
            request, scope='payment_id', limit=10, window=300, identity=query)
        if not allowed:
            messages.error(request, rl_msg)
        elif query:
            result = PaymentIdentifier.objects.filter(
                is_active=True
            ).filter(
                Q(national_id=query) | Q(student_number=query) | Q(payment_id=query)
            ).first()
    context = {
        'accounts': accounts,
        'result': result,
        'query': query,
        'searched': searched,
        'page_title': 'شناسه واریز شهریه',
    }
    return render(request, 'core/payment_id.html', context)


def documents(request):
    """آیین‌نامه‌ها و فرم‌ها — ابتدا پوشه‌های مقطع، سپس فایل‌های داخل هر پوشه."""
    from core.degree_map import document_degree_for_query, normalize_degree_query

    docs = DownloadableDocument.objects.filter(is_active=True)
    raw_degree = request.GET.get('degree', '')
    degree = normalize_degree_query(raw_degree)
    # اگر کد Major آمد، به پوشه سند نگاشت کن
    if degree and degree not in {k for k, _ in DownloadableDocument.DEGREE_LEVEL_CHOICES}:
        degree = document_degree_for_query(degree)
    category = request.GET.get('category', '')
    # «بخش» (آموزش / پژوهش / …) — بدون این فیلتر، دسته‌بندی فقط در پنل
    # دیده می‌شد و کاربر سایت راهی برای جدا کردنشان نداشت
    section_keys = {k for k, _ in DownloadableDocument.SECTION_CHOICES if k}
    section = request.GET.get('section', '')
    if section not in section_keys:
        section = ''
    if section:
        docs = docs.filter(section=section)

    degree_keys = {k for k, _ in DownloadableDocument.DEGREE_LEVEL_CHOICES}
    show_folders = degree not in degree_keys

    folders = []
    if show_folders:
        counts = {
            row['degree_level']: row['n']
            for row in docs.values('degree_level').annotate(n=Count('id'))
        }
        for folder in DownloadableDocument.degree_folder_meta():
            folder = {**folder, 'count': counts.get(folder['key'], 0)}
            folders.append(folder)
        documents = []
        current_degree_label = ''
    else:
        documents = docs.filter(degree_level=degree)
        current_degree_label = dict(DownloadableDocument.DEGREE_LEVEL_CHOICES).get(degree, degree)
        if category in dict(DownloadableDocument.CATEGORY_CHOICES):
            documents = documents.filter(category=category)

    context = {
        'show_folders': show_folders,
        'folders': folders,
        'documents': documents if not show_folders else [],
        'current_degree': degree,
        'current_degree_label': current_degree_label if not show_folders else '',
        'current_category': category,
        'categories': DownloadableDocument.CATEGORY_CHOICES,
        'current_section': section,
        'current_section_label': dict(DownloadableDocument.SECTION_CHOICES).get(section, ''),
        'sections': [(k, v) for k, v in DownloadableDocument.SECTION_CHOICES if k],
        'page_title': 'آیین‌نامه‌ها و فرم‌ها',
    }
    return render(request, 'core/documents.html', context)


def document_detail(request, pk):
    """صفحه مشاهده آیین‌نامه/فرم — اولویت با نمایش داخل سایت، سپس انتخاب PDF یا Word."""
    doc = get_object_or_404(DownloadableDocument, pk=pk, is_active=True)
    fmt = (request.GET.get('view') or '').lower()
    # bool(doc.file) فقط می‌گوید نامی در دیتابیس هست، نه اینکه فایل
    # روی دیسک باشد. صفحه با همان، iframe و دکمهٔ دانلود می‌ساخت و
    # هر دو به ۴۰۴ می‌رسیدند.
    has_pdf = doc.has_file
    has_word = doc.has_word
    has_external = bool(doc.external_url) and not has_pdf and not has_word

    if fmt not in ('pdf', 'word', 'link'):
        if has_pdf:
            fmt = 'pdf'
        elif has_word:
            fmt = 'word'
        elif has_external:
            fmt = 'link'
        else:
            fmt = ''

    if fmt == 'pdf' and not has_pdf:
        fmt = 'word' if has_word else ('link' if has_external else '')
    if fmt == 'word' and not has_word:
        fmt = 'pdf' if has_pdf else ('link' if has_external else '')

    back_degree = doc.degree_level or 'general'
    context = {
        'doc': doc,
        'view_format': fmt,
        'has_pdf': has_pdf,
        'has_word': has_word,
        'has_external': has_external,
        'back_degree': back_degree,
        'page_title': doc.title,
    }
    return render(request, 'core/document_detail.html', context)


def events_list(request):
    """فهرست رویدادها"""
    today = timezone.now().date()
    upcoming = Event.objects.filter(is_active=True, date__gte=today).order_by('date')
    past = Event.objects.filter(is_active=True, date__lt=today).order_by('-date')[:20]
    context = {
        'upcoming': upcoming,
        'past': past,
        'page_title': 'رویدادها',
    }
    return render(request, 'core/events.html', context)


def graduate_studies(request):
    """هاب تحصیلات تکمیلی مطابق سایت رسمی"""
    info = GraduateStudiesInfo.objects.first()
    context = {
        'info': info,
        'page_title': 'تحصیلات تکمیلی',
    }
    return render(request, 'core/graduate_studies.html', context)


def graduate_majors(request):
    """رشته‌های تحصیلات تکمیلی → هاب مسیر دانشجو با فیلتر ارشد."""
    return redirect(reverse('core:student_path') + '?degree=master&step=1')


def graduate_manager(request):
    """مدیر تحصیلات تکمیلی"""
    info = GraduateStudiesInfo.objects.first()
    context = {
        'info': info,
        'page_title': 'مدیر تحصیلات تکمیلی',
    }
    return render(request, 'core/graduate_manager.html', context)


def graduate_news(request):
    """اخبار تحصیلات تکمیلی"""
    news_list = News.objects.filter(
        is_published=True
    ).filter(
        Q(title__icontains='ارشد')
        | Q(title__icontains='تحصیلات تکمیلی')
        | Q(title__icontains='پایان نامه')
        | Q(title__icontains='پایان‌نامه')
        | Q(category__slug__icontains='takmili')
        | Q(category__name__icontains='تحصیلات تکمیلی')
    ).distinct().order_by('-published_at')[:40]
    context = {
        'news_list': news_list,
        'page_title': 'اخبار تحصیلات تکمیلی',
    }
    return render(request, 'core/graduate_news.html', context)


def graduate_regulations(request):
    """سازگاری با لینک‌های قدیمی — هدایت به صفحه واحد آیین‌نامه‌ها و فرم‌ها."""
    params = request.GET.copy()
    if 'degree' not in params:
        params['degree'] = 'master'
    return redirect(f"{reverse('core:documents')}?{params.urlencode()}")


def gallery_view(request):
    images = Gallery.objects.filter(is_active=True, media_type='image')
    context = {
        'images': images,
        'page_title': 'گالری تصاویر',
    }
    return render(request, 'core/gallery.html', context)


# ─── حوزه ریاست ───────────────────────────────────────────────

def presidency(request):
    """ریاست موسسه — رئیس، دفتر، و هیئت رئیسه.

    معاونان از VicePresidency خوانده می‌شوند نه DeputyVice: مدل دوم
    صفر رکورد دارد و همهٔ داده‌های واقعی در اولی است، پس این بخش
    همیشه خالی رندر می‌شد.
    """
    office = PresidencyOffice.objects.first()
    context = {
        'office': office,
        'deputies': VicePresidency.objects.filter(is_active=True),
        'page_title': 'ریاست موسسه',
    }
    return render(request, 'core/presidency.html', context)


def presidency_office(request):
    office = PresidencyOffice.objects.first()
    units = PresidencyOfficeUnit.objects.filter(is_active=True)
    context = {
        'office': office,
        'units': units,
        'page_title': 'دفتر ریاست',
    }
    return render(request, 'core/presidency_office.html', context)


def presidency_office_unit(request, slug):
    unit = get_object_or_404(PresidencyOfficeUnit, slug=slug, is_active=True)
    office = PresidencyOffice.objects.first()
    units = PresidencyOfficeUnit.objects.filter(is_active=True)
    context = {
        'unit': unit,
        'office': office,
        'units': units,
        'page_title': unit.title,
    }
    return render(request, 'core/presidency_office_unit.html', context)


def deputies(request):
    """«معاونین دانشگاه» و «معاونت‌ها» یک چیز بودند با دو صفحه.

    این یکی از DeputyVice می‌خواند که صفر رکورد دارد، پس همیشه صفحهٔ
    خالی نشان می‌داد؛ آن یکی از VicePresidency می‌خواند و داده دارد.
    به‌جای نگه‌داشتن دو صفحه برای یک مفهوم، این نشانی به آن یکی
    هدایت می‌شود تا لینک‌های قدیمی هم نشکنند.
    """
    return redirect('core:vices_list', permanent=True)


def international_office(request):
    office = InternationalOffice.objects.first()
    activities = InternationalActivity.objects.filter(is_active=True)
    agreements = activities.filter(activity_type='agreement')
    exchanges = activities.filter(activity_type='exchange')
    joint_research = activities.filter(activity_type='joint_research')
    conferences = activities.filter(activity_type='conference')
    scholarships = activities.filter(activity_type='scholarship')
    context = {
        'office': office,
        'activities': activities,
        'agreements': agreements,
        'exchanges': exchanges,
        'joint_research': joint_research,
        'conferences': conferences,
        'scholarships': scholarships,
        'page_title': 'دفتر همکاری‌های علمی و بین‌الملل',
    }
    return render(request, 'core/international_office.html', context)


def public_relations(request):
    pr = PublicRelations.objects.first()
    press_releases = PressRelease.objects.filter(is_active=True)
    context = {
        'pr': pr,
        'press_releases': press_releases,
        'page_title': 'مدیریت روابط عمومی',
    }
    return render(request, 'core/public_relations.html', context)


def security_office(request):
    office = SecurityOffice.objects.first()
    context = {
        'office': office,
        'page_title': 'حراست',
    }
    return render(request, 'core/security_office.html', context)


# ─── معاونت‌ها ────────────────────────────────────────────────

def vices_list(request):
    """معاونت‌های موسسه.

    فهرست از context_processor می‌آید (`nav_vices`) — همان ساختاری
    که نوار بالای سایت از آن می‌خواند. پیش از این صفحه فهرست خودش
    را می‌ساخت و ترتیبش با منو یکی نبود.
    """
    return render(request, 'core/vices_list.html', {
        'page_title': 'معاونت‌ها',
    })


def vice_detail(request, vice_type):
    """صفحه جزئیات یک معاونت"""
    VALID = [v[0] for v in VicePresidency.VICE_TYPE_CHOICES]
    if vice_type not in VALID:
        from django.http import Http404
        raise Http404
    vice = VicePresidency.objects.filter(vice_type=vice_type, is_active=True).first()
    units = ViceUnit.objects.filter(vice=vice, is_active=True) if vice else []
    projects = ViceAchievement.objects.filter(vice=vice, is_active=True) if vice else []
    # نام فارسی برای page_title
    label_map = dict(VicePresidency.VICE_TYPE_CHOICES)
    page_title = label_map.get(vice_type, 'معاونت')
    context = {
        'vice': vice,
        'vice_type': vice_type,
        'page_title': page_title,
        'units': units,
        'projects': projects,
    }
    return render(request, 'core/vice_detail.html', context)


def captcha_image(request):
    """تصویر کپچای فعلی.

    هر بار پاسخ تازه‌ای می‌دهد، پس باید کاملاً بدون کش باشد — وگرنه
    دکمهٔ «تصویر تازه» همان عکس قبلی را از حافظهٔ مرورگر برمی‌دارد.
    """
    from django.http import HttpResponse
    from core import captcha

    if request.GET.get('new'):
        captcha.new_challenge(request.session)

    response = HttpResponse(captcha.render(request.session),
                            content_type='image/png')
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    return response
