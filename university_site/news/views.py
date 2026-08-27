from django.db.models import F
from django.shortcuts import render, get_object_or_404
from .models import News, Category, Gallery


def news_list(request):
    category_slug = request.GET.get('category')
    news_type = request.GET.get('type')
    # بدون select_related، قالب برای هر خبر یک پرس‌وجوی جدا برای
    # دسته‌بندی می‌زد: بیست خبر یعنی بیست کوئری اضافه.
    news = News.objects.filter(is_published=True).select_related('category')

    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        news = news.filter(category=category)
    else:
        category = None

    if news_type:
        news = news.filter(news_type=news_type)

    categories = Category.objects.all()
    featured_news = News.objects.filter(
        is_published=True, is_featured=True).select_related('category')[:3]

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
    article = get_object_or_404(
        News.objects.select_related('category'), slug=slug, is_published=True)

    # شمارنده با F: دو بازدید همزمان، مقدار قدیمی را می‌خواندند و
    # هر دو همان عدد + ۱ را می‌نوشتند، پس یکی از بازدیدها گم می‌شد.
    News.objects.filter(pk=article.pk).update(
        views_count=F('views_count') + 1)
    article.views_count += 1

    related_news = News.objects.filter(
        is_published=True,
        category=article.category
    ).exclude(pk=article.pk).select_related('category')[:3]
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
    """گالری یکپارچه — هدایت به مسیر اصلی."""
    from django.shortcuts import redirect
    return redirect('core:gallery')
