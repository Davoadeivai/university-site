from django.urls import path
from . import views

app_name = 'admissions'

urlpatterns = [
    path('', views.admissions_view, name='admissions'),
    # پذیرش — مراحل OTP + فرم
    path('تایید-موبایل/', views.apply_otp_send, name='apply_otp_send'),
    path('تایید-کد/', views.apply_otp_verify, name='apply_otp_verify'),
    path('ثبت-درخواست/', views.apply, name='apply'),
    path('ثبت-موفق/<str:code>/', views.apply_success, name='apply_success'),
    # پیگیری
    path('پیگیری/', views.track_application, name='track'),
    # شهریه
    path('شهریه/', views.tuition_info, name='tuition'),
    path('محاسبه-شهریه/', views.tuition_calculator, name='tuition_calc'),
]
