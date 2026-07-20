from django.urls import path
from django.views.generic import RedirectView
from . import views

app_name = 'core'

urlpatterns = [
    # صفحه اصلی یکپارچه (قبلاً landing + home جدا بودند)
    path('', views.home, name='home'),
    path('خانه/', RedirectView.as_view(pattern_name='core:home', permanent=True)),
    path('landing/', RedirectView.as_view(pattern_name='core:home', permanent=True), name='landing'),
    path('درباره-ما/', views.about, name='about'),
    path('شهر-بهنمیر/', views.city_behnammir, name='city_behnammir'),
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
    path('رویدادها/', views.events_list, name='events'),
    path('تحصیلات-تکمیلی/', views.graduate_studies, name='graduate_studies'),
    # حوزه ریاست
    path('ریاست/', views.presidency, name='presidency'),
    path('دفتر-ریاست/', views.presidency_office, name='presidency_office'),
    path('معاونین/', views.deputies, name='deputies'),
    path('دفتر-بین-الملل/', views.international_office, name='international_office'),
    path('روابط-عمومی/', views.public_relations, name='public_relations'),
    path('حراست/', views.security_office, name='security_office'),
]
