from django.urls import path
from . import views

app_name = 'academics'

urlpatterns = [
    path('دانشکده‌ها/', views.departments_list, name='departments'),
    path('دانشکده‌ها/<path:slug>/', views.department_detail, name='department_detail'),
    path('رشته‌ها/', views.majors_list, name='majors'),
    path('رشته‌ها/<path:slug>/', views.major_detail, name='major_detail'),
    path('تقویم-آموزشی/', views.academic_calendar, name='calendar'),
    path('پنل-دانشجویی/', views.students_panel, name='students_panel'),
    path('پنل-اساتید/', views.professors_panel, name='professors_panel'),
    path('آموزش-الکترونیکی/', views.elearning, name='elearning'),
    path('گروه‌های-آموزشی/', views.groups_list, name='groups_list'),
    path('گروه‌های-آموزشی/<path:slug>/', views.group_detail, name='group_detail'),
]
