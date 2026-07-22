from core.models import SiteSettings, QuickLink
from news.models import News
from accounts.models import Announcement
from academics.models import AcademicGroup, Department


def global_context(request):
    """Global context processor to provide data to all templates"""
    settings = SiteSettings.objects.first()
    quick_links = QuickLink.objects.filter(is_active=True, category='home')[:8]
    footer_quick_access = QuickLink.objects.filter(is_active=True, category='quick_access')
    latest_news_nav = News.objects.filter(is_published=True)[:3]
    urgent_announcements = Announcement.objects.filter(is_active=True, is_urgent=True)[:3]

    # گروه‌های آموزشی برای نمایش در navbar — ادمین می‌تواند از پنل مدیریت ویرایش کند
    nav_groups = AcademicGroup.objects.filter(is_active=True).select_related('department').order_by('order', 'name')
    nav_departments = Department.objects.filter(is_active=True).prefetch_related('groups').order_by('order')

    return {
        'site_settings': settings,
        'global_quick_links': quick_links,
        'footer_quick_access': footer_quick_access,
        'latest_news_nav': latest_news_nav,
        'urgent_announcements': urgent_announcements,
        'nav_groups': nav_groups,
        'nav_departments': nav_departments,
    }
