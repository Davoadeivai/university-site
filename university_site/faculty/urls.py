from django.urls import path
from . import views

app_name = 'faculty'

urlpatterns = [
    path('', views.professors_list, name='list'),
    path('<slug:slug>/', views.professor_detail, name='professor_detail'),
]
