from django.urls import path
from . import views

app_name = 'admissions'

urlpatterns = [
    path('', views.admissions_view, name='admissions'),
    path('ثبت-درخواست/', views.apply, name='apply'),
]
