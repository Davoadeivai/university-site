from django.urls import path
from . import views

app_name = 'library'

urlpatterns = [
    path('', views.library_home, name='library'),
    path('کتاب/<int:pk>/', views.book_detail, name='book_detail'),
    path('مقالات/', views.articles_list, name='articles'),
    path('مقالات-اعضای-هیات-علمی/', views.faculty_articles, name='faculty_articles'),
    path('بانک-مقالات-همایش-ها/', views.conference_articles, name='conference_articles'),
    path('مقالات/<int:pk>/', views.article_detail, name='article_detail'),
    path('عضویت/', views.membership, name='membership'),
]
