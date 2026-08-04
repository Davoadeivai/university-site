from django.urls import path
from . import views

app_name = 'faculty'

urlpatterns = [
    path('', views.professors_list, name='list'),
    # اسلاگ فارسی است (allow_unicode=True) و مبدل `slug` جنگو فقط ASCII
    # می‌پذیرد؛ با آن، افزودن استادی با نام فارسی صفحهٔ اصلی را ۵۰۰ می‌کرد.
    path('<path:slug>/', views.professor_detail, name='professor_detail'),
]
