from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify


class Category(models.Model):
    CATEGORY_CHOICES = [
        ('academic', 'آموزشی'),
        ('research', 'پژوهشی'),
        ('cultural', 'فرهنگی'),
        ('administrative', 'اداری'),
        ('competitions', 'مسابقات'),
        ('conferences', 'همایش‌ها'),
        ('announcement', 'اطلاعیه'),
    ]
    name = models.CharField(_('نام دسته'), max_length=100)
    slug = models.SlugField(unique=True, allow_unicode=True)
    category_type = models.CharField(_('نوع'), max_length=30, choices=CATEGORY_CHOICES, default='academic')
    icon = models.CharField(_('آیکون'), max_length=100, default='fas fa-newspaper')
    color = models.CharField(_('رنگ'), max_length=20, default='primary')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = _('دسته‌بندی')
        verbose_name_plural = _('دسته‌بندی‌ها')
        ordering = ['order']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('news:category', args=[self.slug])


class News(models.Model):
    TYPE_CHOICES = [
        ('news', 'خبر'),
        ('announcement', 'اطلاعیه'),
        ('event', 'رویداد'),
    ]
    title = models.CharField(_('عنوان'), max_length=300)
    slug = models.SlugField(unique=True, allow_unicode=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True,
                                  verbose_name=_('دسته‌بندی'), related_name='news')
    news_type = models.CharField(_('نوع'), max_length=20, choices=TYPE_CHOICES, default='news')
    summary = models.TextField(_('خلاصه'), max_length=500)
    content = models.TextField(_('محتوا'))
    image = models.ImageField(_('تصویر'), upload_to='news/', blank=True, null=True)
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('نویسنده'))
    is_featured = models.BooleanField(_('خبر برجسته'), default=False)
    is_published = models.BooleanField(_('منتشرشده'), default=True)
    views_count = models.PositiveIntegerField(_('تعداد بازدید'), default=0)
    published_at = models.DateTimeField(_('تاریخ انتشار'), auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('خبر')
        verbose_name_plural = _('اخبار')
        ordering = ['-published_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('news:detail', args=[self.slug])


class Gallery(models.Model):
    MEDIA_TYPES = [('image', 'تصویر'), ('video', 'ویدئو')]
    title = models.CharField(_('عنوان'), max_length=200)
    media_type = models.CharField(_('نوع'), max_length=10, choices=MEDIA_TYPES, default='image')
    image = models.ImageField(_('تصویر'), upload_to='gallery/', blank=True, null=True)
    video_url = models.URLField(_('لینک ویدئو'), blank=True)
    description = models.TextField(_('توضیحات'), blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('گالری')
        verbose_name_plural = _('گالری')
        ordering = ['-created_at']

    def __str__(self):
        return self.title
