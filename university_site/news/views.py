from django.shortcuts import render, get_object_or_404
from .models import News, Category, Gallery


def news_list(request):
    category_slug = request.GET.get('category')
    news_type = request.GET.get('type')
    news = News.objects.filter(is_published=True)

    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        news = news.filter(category=category)
    else:
        category = None

    if news_type:
        news = news.filter(news_type=news_type)

    categories = Category.objects.all()
    featured_news = News.objects.filter(is_published=True, is_featured=True)[:3]

    context = {
        'news': news,
        'categories': categories,
        'current_category': category,
        'news_type': news_type,
        'featured_news': featured_news,
        'page_title': 'اخبار و اطلاعیه‌ها',
    }
    return render(request, 'news/news_list.html', context)


def news_detail(request, slug):
    article = get_object_or_404(News, slug=slug, is_published=True)
    article.views_count += 1
    article.save(update_fields=['views_count'])
    related_news = News.objects.filter(
        is_published=True,
        category=article.category
    ).exclude(pk=article.pk)[:3]
    context = {
        'article': article,
        'related_news': related_news,
        'page_title': article.title,
    }
    return render(request, 'news/news_detail.html', context)


def announcements(request):
    items = News.objects.filter(is_published=True, news_type='announcement')
    context = {
        'items': items,
        'page_title': 'اطلاعیه‌ها',
    }
    return render(request, 'news/announcements.html', context)


def gallery_media(request):
    images = Gallery.objects.filter(is_active=True, media_type='image')
    videos = Gallery.objects.filter(is_active=True, media_type='video')
    context = {
        'images': images,
        'videos': videos,
        'page_title': 'گالری تصاویر و ویدئوها',
    }
    return render(request, 'news/gallery.html', context)
