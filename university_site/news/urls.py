from django.urls import path, re_path

from . import views
from .feeds import NewsAtomFeed, NewsFeed

app_name = 'news'

urlpatterns = [
    path('', views.news_list, name='list'),
    path('اطلاعیه‌ها/', views.announcements, name='announcements'),
    path('گالری/', views.gallery_media, name='gallery'),
    # پیش از مسیر عمومیِ پایین می‌آیند، وگرنه «rss» را عنوان یک خبر
    # می‌گیرد و به ۴۰۴ می‌رسد.
    path('rss/', NewsFeed(), name='feed'),
    path('atom/', NewsAtomFeed(), name='feed_atom'),
    # Unicode slugs for Persian announcement titles
    re_path(r'^(?P<slug>[-a-zA-Z0-9_\u0600-\u06FF]+)/$', views.news_detail, name='detail'),
]
