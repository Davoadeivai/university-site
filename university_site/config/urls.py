from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
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
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
