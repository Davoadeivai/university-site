from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count
from django.utils import timezone
from django.db.models import Q

from core.models import (
    SiteSettings, Slider, QuickLink, Event, FAQ, InstitutionGoal, BoardMember,
    CityInfo, CityAttraction,
    PresidencyOffice, DeputyVice,
    InternationalOffice, InternationalActivity,
    PublicRelations, PressRelease,
    SecurityOffice,
    VicePresidency, ViceUnit, ViceAchievement,
    OrganizationalChart,
    BankAccount, PaymentIdentifier, DownloadableDocument,
)
from news.models import News, Category, Gallery
from academics.models import Department, Major, AcademicCalendar
from faculty.models import Professor
from contact.models import Alumni
from research.models import ResearchProject, Conference


def home(request):
    """صفحه اصلی یکپارچه سایت (جایگزین landing + home قبلی)."""
    settings = SiteSettings.objects.first()
    sliders = list(Slider.objects.filter(is_active=True).order_by('order')[:5])
    quick_links = QuickLink.objects.filter(is_active=True)[:8]
    featured_news = News.objects.filter(is_published=True, is_featured=True)[:3]
    latest_news = News.objects.filter(is_published=True)[:6]
    announcements_qs = News.objects.filter(is_published=True, news_type='announcement')
    announcements = announcements_qs[:8]
    # تب‌های اطلاعیه شبیه aab.ac.ir
    announcement_tabs = [
        ('all', 'همه', announcements_qs[:8]),
        ('academic', 'آموزش', announcements_qs.filter(category__category_type='academic')[:8]),
        ('cultural', 'دانشجویی و فرهنگی', announcements_qs.filter(category__category_type='cultural')[:8]),
        ('administrative', 'اداری و مالی', announcements_qs.filter(category__category_type='administrative')[:8]),
        ('research', 'پژوهشی', announcements_qs.filter(category__category_type='research')[:8]),
    ]
    upcoming_events = Event.objects.filter(is_active=True, date__gte=timezone.now().date()).order_by('date')[:4]
    departments = Department.objects.filter(is_active=True)[:6]
    calendar_items = AcademicCalendar.objects.filter(
        start_date__gte=timezone.now().date()
    ).order_by('start_date')[:5]
    featured_professors = Professor.objects.filter(is_active=True).order_by('order')[:4]
    faqs = FAQ.objects.filter(is_active=True)[:6]
    gallery_images = Gallery.objects.filter(is_active=True, media_type='image')[:8]
    alumni = Alumni.objects.filter(is_featured=True)[:4]
    bank_accounts = BankAccount.objects.filter(is_active=True)[:3]

    context = {
        'settings': settings,
        'sliders': sliders,
        'quick_links': quick_links,
        'featured_news': featured_news,
        'latest_news': latest_news,
        'announcements': announcements,
        'announcement_tabs': announcement_tabs,
        'upcoming_events': upcoming_events,
        'departments': departments,
        'calendar_items': calendar_items,
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
        'page_title': 'آشنایی با شهر بهنمیر',
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
        'page_title': 'هیات امنا دانشگاه',
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
    context = {
        'page_title': 'خدمات الکترونیکی',
        'settings': settings,
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
        allowed, rl_msg = check_rate_limit(request, scope='payment_id', limit=10, window=300)
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
    """آیین‌نامه‌ها و فرم‌ها"""
    docs = DownloadableDocument.objects.filter(is_active=True)
    category = request.GET.get('category', '')
    if category in dict(DownloadableDocument.CATEGORY_CHOICES):
        docs = docs.filter(category=category)
    context = {
        'documents': docs,
        'current_category': category,
        'categories': DownloadableDocument.CATEGORY_CHOICES,
        'page_title': 'آیین‌نامه‌ها و فرم‌ها',
    }
    return render(request, 'core/documents.html', context)


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
    """هاب تحصیلات تکمیلی (کارشناسی ارشد و دکتری)"""
    master_majors = Major.objects.filter(is_active=True, degree='master').select_related('group')
    phd_majors = Major.objects.filter(is_active=True, degree='phd').select_related('group')
    context = {
        'master_majors': master_majors,
        'phd_majors': phd_majors,
        'page_title': 'تحصیلات تکمیلی',
    }
    return render(request, 'core/graduate_studies.html', context)


def gallery_view(request):
    images = Gallery.objects.filter(is_active=True, media_type='image')
    videos = Gallery.objects.filter(is_active=True, media_type='video')
    context = {
        'images': images,
        'videos': videos,
        'page_title': 'گالری',
    }
    return render(request, 'core/gallery.html', context)


# ─── حوزه ریاست ───────────────────────────────────────────────

def presidency(request):
    office = PresidencyOffice.objects.first()
    deputies = DeputyVice.objects.filter(is_active=True)
    context = {
        'office': office,
        'deputies': deputies,
        'page_title': 'ریاست',
    }
    return render(request, 'core/presidency.html', context)


def presidency_office(request):
    office = PresidencyOffice.objects.first()
    context = {
        'office': office,
        'page_title': 'دفتر ریاست',
    }
    return render(request, 'core/presidency_office.html', context)


def deputies(request):
    all_deputies = DeputyVice.objects.filter(is_active=True)
    context = {
        'deputies': all_deputies,
        'page_title': 'معاونین دانشگاه',
    }
    return render(request, 'core/deputies.html', context)


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
    """صفحه معرفی همه معاونت‌ها"""
    vices = VicePresidency.objects.filter(is_active=True)
    context = {
        'vices': vices,
        'page_title': 'معاونت‌های دانشگاه',
    }
    return render(request, 'core/vices_list.html', context)


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
