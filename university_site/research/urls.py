from django.urls import path
from . import views

app_name = 'research'

urlpatterns = [
    path('', views.research_home, name='research'),
    path('پایان-نامه‌ها/', views.theses_list, name='theses'),
    path('همایش‌ها/', views.conferences_list, name='conferences'),
]
