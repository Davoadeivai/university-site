from django.urls import path
from . import views

app_name = 'contact'

urlpatterns = [
    path('تماس-با-ما/', views.contact, name='contact'),
    path('فارغ-التحصیلان/', views.alumni, name='alumni'),
    path('ارتباط-با-صنعت/', views.industry, name='industry'),
]
