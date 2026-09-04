from django.urls import path

from . import views

app_name = 'directory'

urlpatterns = [
    path('دفترچه-تلفن/', views.staff_directory, name='staff'),
    path('اعضای-موسسه/', views.academic_people, name='people'),
    path('اعضای-موسسه/<str:slug>/', views.academic_people_section,
         name='people_section'),
    path('سرفصل-دروس/', views.curriculum_list, name='curricula'),
    path('سرفصل-دروس/<int:pk>/دریافت/', views.curriculum_download, name='curriculum_download'),
    path('منابع-پژوهشی/', views.resources, name='resources'),
]
