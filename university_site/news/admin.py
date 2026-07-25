from django.contrib import admin

from core.admin_jalali import JalaliAdminMixin
from .models import News, Category, Gallery


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category_type', 'order']
    list_editable = ['order']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(News)
class NewsAdmin(JalaliAdminMixin, admin.ModelAdmin):
    list_display = ['title', 'news_type', 'category', 'is_featured', 'is_published', 'views_count', 'published_jalali']
    list_filter = ['news_type', 'category', 'is_featured', 'is_published']
    list_editable = ['is_featured', 'is_published']
    search_fields = ['title', 'summary', 'content']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['views_count']


@admin.register(Gallery)
class GalleryAdmin(JalaliAdminMixin, admin.ModelAdmin):
    list_display = ['title', 'media_type', 'is_active', 'created_jalali']
    list_filter = ['media_type', 'is_active']
    list_editable = ['is_active']
