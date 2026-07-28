from django.core.cache import cache

from core.models import SiteSettings, QuickLink
from news.models import News
from accounts.models import Announcement
from academics.models import AcademicGroup, Department

_CACHE_TTL = 60  # seconds — short so admin edits show quickly


def global_context(request):
    """Global context processor — cached to cut DB hits on every page."""
    cached = cache.get('global_context_v1')
    if cached is not None:
        return cached

    settings = SiteSettings.objects.first()
    quick_links = list(QuickLink.objects.filter(is_active=True, category='home')[:8])
    footer_quick_access = list(QuickLink.objects.filter(is_active=True, category='quick_access'))
    latest_news_nav = list(News.objects.filter(is_published=True)[:3])
    urgent_announcements = list(Announcement.objects.filter(is_active=True, is_urgent=True)[:3])

    nav_groups = list(
        AcademicGroup.objects.filter(is_active=True)
        .exclude(slug__iexact='bargh')
        .exclude(name__iexact='bargh')
        .select_related('department')
        .order_by('order', 'name')
    )
    nav_departments = list(
        Department.objects.filter(is_active=True).prefetch_related('groups').order_by('order')
    )

    data = {
        'site_settings': settings,
        'global_quick_links': quick_links,
        'footer_quick_access': footer_quick_access,
        'latest_news_nav': latest_news_nav,
        'urgent_announcements': urgent_announcements,
        'nav_groups': nav_groups,
        'nav_departments': nav_departments,
    }
    cache.set('global_context_v1', data, _CACHE_TTL)
    return data
