from django.core.cache import cache

from core.models import SiteSettings, QuickLink, HomeSection
from news.models import News
from accounts.models import Announcement
from academics.models import AcademicGroup, Department

_CACHE_TTL = 60  # seconds — short so admin edits show quickly

CACHE_KEY = 'global_context_v1'


def global_context(request):
    """Context سراسری — بخش سنگین کش می‌شود، ظاهر بخش‌ها همیشه تازه است."""
    cached = cache.get(CACHE_KEY)

    if cached is None:
        settings = SiteSettings.objects.first()
        quick_links = list(QuickLink.objects.filter(is_active=True, category='home')[:8])
        footer_quick_access = list(
            QuickLink.objects.filter(is_active=True, category='quick_access')
        )
        latest_news_nav = list(News.objects.filter(is_published=True)[:3])
        urgent_announcements = list(
            Announcement.objects.filter(is_active=True, is_urgent=True)[:3]
        )

        nav_groups = list(
            AcademicGroup.objects.filter(is_active=True)
            .exclude(slug__iexact='bargh')
            .exclude(name__iexact='bargh')
            .select_related('department')
            .order_by('order', 'name')
        )
        nav_departments = list(
            Department.objects.filter(is_active=True)
            .prefetch_related('groups').order_by('order')
        )

        # معاونت‌ها برای صفحه‌ها (نه منو). منوی معاونین از بند ۱۳ سند
        # اصلاحات ترتیب ثابتی دارد و در قالب نوشته شده؛ این فهرست
        # جاهای دیگری که به داده نیاز دارند را تغذیه می‌کند.
        from core.models import VicePresidency
        nav_vices = list(
            VicePresidency.objects.filter(is_active=True).order_by('vice_type')
        )

        # گروه‌های دارای تحصیلات تکمیلی — بند ۱۷ سند اصلاحات
        nav_graduate_groups = list(
            AcademicGroup.objects.filter(is_active=True, has_graduate=True)
            .order_by('graduate_order', 'name')
        )

        cached = {
            'site_settings': settings,
            'global_quick_links': quick_links,
            'footer_quick_access': footer_quick_access,
            'latest_news_nav': latest_news_nav,
            'urgent_announcements': urgent_announcements,
            'nav_groups': nav_groups,
            'nav_departments': nav_departments,
            'nav_vices': nav_vices,
            'nav_graduate_groups': nav_graduate_groups,
        }
        cache.set(CACHE_KEY, cached, _CACHE_TTL)

    # ظاهر بخش‌های صفحهٔ اصلی — کش نمی‌شود.
    # جدول ۱۲ ردیفی است و صرفهٔ کش‌کردنش کمتر از هزینهٔ آن است: با کش،
    # پنهان/نمایان کردن یک بخش یا تغییر عنوان تا ۶۰ ثانیه دیده نمی‌شد و
    # روی سرور که هر worker کش جدا دارد، کاربران حالت‌های متفاوت می‌دیدند.
    # در قالب با کلید در دسترس است: sections.features.image
    data = dict(cached)
    data['sections'] = {s.key: s for s in HomeSection.objects.all()}
    return data
