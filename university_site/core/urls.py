from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.landing, name='landing'),
    path('خانه/', views.home, name='home'),
    path('درباره-ما/', views.about, name='about'),
    path('اهداف-موسسه/', views.institution_goals, name='institution_goals'),
    path('هیات-موسس/', views.board_founders, name='board_founders'),
    path('هیات-امنا/', views.board_trustees, name='board_trustees'),
    path('معاونت‌ها/', views.vices_list, name='vices_list'),
    path('معاونت‌ها/<str:vice_type>/', views.vice_detail, name='vice_detail'),
    path('search/', views.search, name='search'),
    path('سوالات-متداول/', views.faq_view, name='faq'),
    path('خدمات-الکترونیکی/', views.eservices, name='eservices'),
    path('گالری/', views.gallery_view, name='gallery'),
    path('شهر-بهنمیر/', views.city_behnamir, name='city_behnamir'),
    # حوزه ریاست
    path('ریاست/', views.presidency, name='presidency'),
    path('دفتر-ریاست/', views.presidency_office, name='presidency_office'),
    path('معاونین/', views.deputies, name='deputies'),
    path('دفتر-بین-الملل/', views.international_office, name='international_office'),
    path('روابط-عمومی/', views.public_relations, name='public_relations'),
    path('حراست/', views.security_office, name='security_office'),
]
