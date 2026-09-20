from django.urls import path, re_path

from . import views

app_name = 'news'

# خوراک خبری (RSS/Atom) به خواست موسسه برداشته شد.
#
# سالی که روی سایت بود، نه کسی مشترکش شد و نه جایی نشانش داده
# می‌شد؛ فقط دو مسیر و یک ماژول بود که باید نگه داشته می‌شد.

urlpatterns = [
    path('', views.news_list, name='list'),
    path('اطلاعیه‌ها/', views.announcements, name='announcements'),
    path('گالری/', views.gallery_media, name='gallery'),
    # Unicode slugs for Persian announcement titles
    re_path(r'^(?P<slug>[-a-zA-Z0-9_\u0600-\u06FF]+)/$', views.news_detail, name='detail'),
]
