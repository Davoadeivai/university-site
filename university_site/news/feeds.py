"""خوراک خبری (RSS/Atom) — اطلاع‌رسانی بدون آنکه کسی سر بزند.

سایت تا امروز فقط یک راه برای رساندن خبر داشت: اینکه بازدیدکننده
خودش بیاید و ببیند. خوراک، همان خبرها را به خواننده‌خوان‌ها،
کانال‌های خبری و سرویس‌های بازنشر می‌دهد، بی‌آنکه چیزی در پنل
عوض شود — هرچه در «اخبار» منتشر شود، همان‌جا هم می‌رود.
"""
from django.contrib.syndication.views import Feed
from django.urls import reverse
from django.utils.feedgenerator import Atom1Feed

from .models import News


class NewsFeed(Feed):
    """بیست خبر و اطلاعیهٔ آخر."""

    title = 'پایگاه خبری موسسه آموزش عالی علامه امینی'
    description = 'اخبار، اطلاعیه‌ها و رویدادهای موسسه'
    # عنوان و توضیح فارسی است؛ بدون زبان، خواننده‌خوان راست‌چین نمی‌کند.
    language = 'fa-ir'

    def link(self):
        return reverse('news:list')

    def items(self):
        return (News.objects.filter(is_published=True)
                .select_related('category')
                .order_by('-published_at')[:20])

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.summary

    def item_pubdate(self, item):
        return item.published_at

    def item_categories(self, item):
        return [item.category.name] if item.category_id else []


class NewsAtomFeed(NewsFeed):
    feed_type = Atom1Feed
    subtitle = NewsFeed.description
