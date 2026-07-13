from django.urls import path
from . import views

app_name = 'news'

urlpatterns = [
    path('', views.news_list, name='list'),
    path('اطلاعیه‌ها/', views.announcements, name='announcements'),
    path('گالری/', views.gallery_media, name='gallery'),
    path('<slug:slug>/', views.news_detail, name='detail'),
]
