from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns

from core import private_media
from core.admin_finance import finance_overview
from core.admin_search import admin_live_counters, admin_nav_search_index, public_live_search

urlpatterns = [
    # پرونده‌های حساس از اینجا رد می‌شوند، نه از دست وب‌سرور.
    #
    # پیش از این هر چیزی زیر \u200E/media/\u200E برای همه باز بود: کارت ملی
    # داوطلب، فیش واریزی دانشجو، مدرک تخفیف شهریه. این مسیر پیش از
    # \u200Estatic()\u200E می‌آید تا در توسعهٔ محلی هم همان قاعده برقرار باشد.
    re_path(r'^media/(?P<path>.+)$', private_media.serve,
            name='private_media'),
    # بدون این، خزنده‌ها /admin/ و /dashboard/ را هم می‌بینند.
    path('robots.txt', TemplateView.as_view(
        template_name='robots.txt', content_type='text/plain'),
        name='robots'),
    path('i18n/', include('django.conf.urls.i18n')),
    path('admin/nav-search.json', admin_nav_search_index, name='admin_nav_search'),
    path('admin/live-counters.json', admin_live_counters, name='admin_live_counters'),
    path('admin/finance-overview/', finance_overview, name='admin_finance_overview'),
    path('api/live-search/', public_live_search, name='public_live_search'),
    path('admin/', admin.site.urls),
    path('', include('core.urls', namespace='core')),
    path('اخبار/', include('news.urls', namespace='news')),
    path('آموزش/', include('academics.urls', namespace='academics')),
    path('اساتید/', include('faculty.urls', namespace='faculty')),
    path('پژوهش/', include('research.urls', namespace='research')),
    path('کتابخانه/', include('library.urls', namespace='library')),
    path('پذیرش/', include('admissions.urls', namespace='admissions')),
    path('', include('contact.urls', namespace='contact')),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('dashboard/', include('dashboard.urls', namespace='dashboard')),
    path('', include('directory.urls', namespace='directory')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
