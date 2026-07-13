from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count
from django.utils import timezone
from news.models import News
from admissions.models import Application
from contact.models import ContactMessage
from core.models import PageView


@login_required
def dashboard(request):
    total_news = News.objects.filter(is_published=True).count()
    total_applications = Application.objects.count()
    new_messages = ContactMessage.objects.filter(status='new').count()
    total_users = User.objects.count()

    recent_news = News.objects.filter(is_published=True).order_by('-published_at')[:5]
    recent_applications = Application.objects.order_by('-created_at')[:5]
    recent_messages = ContactMessage.objects.filter(status='new').order_by('-created_at')[:5]

    context = {
        'total_news': total_news,
        'total_applications': total_applications,
        'new_messages': new_messages,
        'total_users': total_users,
        'recent_news': recent_news,
        'recent_applications': recent_applications,
        'recent_messages': recent_messages,
        'page_title': 'داشبورد مدیریت',
    }
    return render(request, 'dashboard/dashboard.html', context)
