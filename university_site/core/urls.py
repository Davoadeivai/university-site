from django.urls import path
from django.views.generic import RedirectView
from . import views
from . import student_path as student_path_views

app_name = 'core'

urlpatterns = [
    # صفحه اصلی یکپارچه (قبلاً landing + home جدا بودند)
    path('', views.home, name='home'),
    path('مسیر-دانشجو/', student_path_views.student_path, name='student_path'),
    path(
        'مسیر-دانشجو/رشته/<path:slug>/',
        student_path_views.student_path_select_major,
        name='student_path_major',
    ),
    path('خانه/', RedirectView.as_view(pattern_name='core:home', permanent=True)),
    path('landing/', RedirectView.as_view(pattern_name='core:home', permanent=True), name='landing'),
    path('درباره-ما/', views.about, name='about'),
    path('شهر-بابلسر/', views.city_behnammir, name='city_behnammir'),
    # نشانی قدیمی؛ لینک‌های بیرونی و نتایج گوگل نباید ۴۰۴ بگیرند
    path('شهر-بهنمیر/', RedirectView.as_view(
        pattern_name='core:city_behnammir', permanent=True)),
    path('اهداف-موسسه/', views.institution_goals, name='institution_goals'),
    path('هیات-موسس/', views.board_founders, name='board_founders'),
    path('هیات-امنا/', views.board_trustees, name='board_trustees'),
    path('معاونت‌ها/', views.vices_list, name='vices_list'),
    path('معاونت‌ها/<str:vice_type>/', views.vice_detail, name='vice_detail'),
    path('search/', views.search, name='search'),
    path('سوالات-متداول/', views.faq_view, name='faq'),
    path('خدمات-الکترونیکی/', views.eservices, name='eservices'),
    path('گالری/', views.gallery_view, name='gallery'),
    path('شناسه-واریز/', views.payment_id, name='payment_id'),
    path('آیین-نامه-ها-و-فرم-ها/', views.documents, name='documents'),
    path('آیین-نامه-ها-و-فرم-ها/<int:pk>/', views.document_detail, name='document_detail'),
    # سازگاری با لینک‌هایی که نیم‌فاصله (ZWNJ) به‌جای خط تیره دارند
    path(
        'آیین-نامه‌ها-و-فرم‌ها/',
        RedirectView.as_view(pattern_name='core:documents', permanent=False, query_string=True),
    ),
    path(
        'آیین-نامه‌ها-و-فرم‌ها/<int:pk>/',
        RedirectView.as_view(pattern_name='core:document_detail', permanent=False, query_string=True),
    ),
    path('رویدادها/', views.events_list, name='events'),
    path('تحصیلات-تکمیلی/', views.graduate_studies, name='graduate_studies'),
    path('تحصیلات-تکمیلی/رشته-ها/', views.graduate_majors, name='graduate_majors'),
    path('تحصیلات-تکمیلی/مدیر/', views.graduate_manager, name='graduate_manager'),
    path('تحصیلات-تکمیلی/اخبار/', views.graduate_news, name='graduate_news'),
    path('تحصیلات-تکمیلی/آیین-نامه-ها-و-فرم-ها/', views.graduate_regulations, name='graduate_regulations'),
    path(
        'تحصیلات-تکمیلی/آیین-نامه‌ها-و-فرم‌ها/',
        RedirectView.as_view(pattern_name='core:graduate_regulations', permanent=False, query_string=True),
    ),
    # حوزه ریاست
    path('ریاست/', views.presidency, name='presidency'),
    path('دفتر-ریاست/', views.presidency_office, name='presidency_office'),
    path('دفتر-ریاست/<path:slug>/', views.presidency_office_unit, name='presidency_office_unit'),
    path('معاونین/', views.deputies, name='deputies'),
    path('دفتر-بین-الملل/', views.international_office, name='international_office'),
    path('روابط-عمومی/', views.public_relations, name='public_relations'),
    path('حراست/', views.security_office, name='security_office'),
]
