from django.urls import path
from . import views

app_name = 'research'

urlpatterns = [
    path('', views.research_home, name='research'),
    path('پروژه‌ها/', views.projects_list, name='projects'),
    path('پروژه‌ها/<int:pk>/', views.project_detail, name='project_detail'),
    path('پایان-نامه‌ها/', views.theses_list, name='theses'),
    path('پایان-نامه‌ها/<int:pk>/', views.thesis_detail, name='thesis_detail'),
    path('همایش‌ها/', views.conferences_list, name='conferences'),
    path('همایش‌ها/<int:pk>/', views.conference_detail, name='conference_detail'),
    path('مجلات/', views.journals_list, name='journals'),
    path('مجلات/<path:slug>/', views.journal_detail, name='journal_detail'),
]
