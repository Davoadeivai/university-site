from django.contrib import admin
from django.utils.html import format_html

from .models import CurriculumDocument, DirectoryPerson, ExternalResource


@admin.register(DirectoryPerson)
class DirectoryPersonAdmin(admin.ModelAdmin):
    list_display = [
        'thumb', 'display_name', 'category', 'position', 'field_of_study',
        'degree', 'extension', 'order', 'is_active',
    ]
    list_display_links = ['thumb', 'display_name']
    list_editable = ['order', 'is_active']
    list_filter = ['category', 'degree', 'is_active']
    search_fields = [
        'full_name', 'first_name', 'last_name', 'position',
        'field_of_study', 'extension', 'phone', 'email',
    ]
    list_per_page = 50
    ordering = ['category', 'order', 'full_name']

    fieldsets = (
        ('دسته‌بندی', {
            'fields': ('category', 'order', 'is_active'),
            'description': 'دسته تعیین می‌کند این فرد در کدام صفحهٔ سایت دیده شود.',
        }),
        ('نام', {
            'fields': ('honorific', 'first_name', 'last_name', 'full_name'),
            'description': 'پیشوند («دکتر»، «مهندس») را جدا بنویسید تا مرتب‌سازی '
                           'الفبایی درست کار کند. اگر «نام و نام خانوادگی» را '
                           'خالی بگذارید، از دو فیلد قبلی ساخته می‌شود.',
        }),
        ('اطلاعات علمی و سازمانی', {
            'fields': ('position', 'field_of_study', 'degree'),
        }),
        ('تماس و تصویر', {
            'fields': ('extension', 'phone', 'email', 'photo'),
        }),
    )

    @admin.display(description='تصویر')
    def thumb(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" style="width:38px;height:38px;object-fit:cover;'
                'border-radius:50%;border:1px solid #dbe4ef">', obj.photo.url)
        return format_html(
            '<span style="display:inline-flex;align-items:center;'
            'justify-content:center;width:38px;height:38px;border-radius:50%;'
            'background:#f3f7fc;color:#5b6e82;font-size:15px">—</span>')


@admin.register(CurriculumDocument)
class CurriculumDocumentAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'level', 'major', 'approved_on', 'size_display',
        'download_link', 'download_count', 'order', 'is_active',
    ]
    list_editable = ['order', 'is_active']
    list_filter = ['level', 'is_active']
    search_fields = ['title', 'note', 'approved_on']
    autocomplete_fields = ['major']
    list_select_related = ['major']
    list_per_page = 50
    readonly_fields = ['size_display', 'download_count']

    fieldsets = (
        (None, {
            'fields': ('title', 'level', 'major', 'file'),
        }),
        ('اطلاعات سند', {
            'fields': ('approved_on', 'note', 'size_display', 'download_count'),
        }),
        ('نمایش', {
            'fields': ('order', 'is_active'),
        }),
    )

    @admin.display(description='حجم', ordering='file_size')
    def size_display(self, obj):
        return obj.size_display or '—'

    @admin.display(description='فایل')
    def download_link(self, obj):
        if not obj.file:
            return '—'
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">دریافت</a>', obj.file.url)


@admin.register(ExternalResource)
class ExternalResourceAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'link', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['title', 'url', 'description']

    @admin.display(description='نشانی')
    def link(self, obj):
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">{}</a>', obj.url, obj.url)
