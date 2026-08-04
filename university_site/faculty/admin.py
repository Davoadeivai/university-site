from django.contrib import admin
from django.utils.html import format_html

from .models import Professor, Publication


class PublicationInline(admin.TabularInline):
    model = Publication
    extra = 0
    fields = ['title', 'pub_type', 'year', 'journal_conference']


@admin.register(Professor)
class ProfessorAdmin(admin.ModelAdmin):
    list_display = ['avatar', 'get_full_name', 'department', 'rank',
                    'is_featured', 'is_active', 'order']
    list_display_links = ['avatar', 'get_full_name']
    list_filter = ['is_featured', 'rank', 'status', 'department', 'is_active']
    list_editable = ['order', 'is_active', 'is_featured']
    search_fields = ['first_name', 'last_name', 'email', 'specialization']
    list_select_related = ('department',)
    prepopulated_fields = {'slug': ('first_name', 'last_name')}
    inlines = [PublicationInline]
    actions = ['mark_featured', 'unmark_featured']
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('first_name', 'last_name', 'slug', 'photo',
                       'rank', 'status', 'department'),
        }),
        ('نمایش', {
            'fields': ('is_featured', 'is_active', 'order'),
            'description': (
                'بخش «هیئت علمی برگزیده» در صفحهٔ اصلی، چهار استاد نخست از '
                'میان علامت‌خورده‌ها را نشان می‌دهد. اگر هیچ‌کس علامت نخورده '
                'باشد، چهار نفر اول بر اساس «ترتیب» نمایش داده می‌شوند.'
            ),
        }),
        ('اطلاعات تماس', {'fields': ('email', 'phone', 'office', 'office_hours')}),
        ('علمی', {'fields': ('bio', 'education', 'specialization', 'research_interests')}),
        ('لینک‌ها', {'fields': ('personal_website', 'google_scholar', 'linkedin', 'researchgate')}),
    )

    @admin.display(description='عکس')
    def avatar(self, obj):
        """تصویر کوچک — نبودِ عکس در فهرست فوراً دیده می‌شود."""
        if obj.photo:
            return format_html(
                '<img src="{}" style="width:38px;height:38px;border-radius:50%;'
                'object-fit:cover;border:1px solid #dbe4ef">', obj.photo.url)
        return format_html(
            '<span title="بدون عکس" style="display:inline-flex;width:38px;'
            'height:38px;border-radius:50%;background:#eef2f7;color:#8496a8;'
            'align-items:center;justify-content:center">؟</span>')

    @admin.action(description='نمایش در صفحه اصلی')
    def mark_featured(self, request, queryset):
        n = queryset.update(is_featured=True)
        self.message_user(request, '%d استاد به صفحه اصلی اضافه شد.' % n)

    @admin.action(description='حذف از صفحه اصلی')
    def unmark_featured(self, request, queryset):
        n = queryset.update(is_featured=False)
        self.message_user(request, '%d استاد از صفحه اصلی برداشته شد.' % n)


@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    list_display = ['title', 'professor', 'pub_type', 'year']
    list_filter = ['pub_type', 'year']
    search_fields = ['title', 'professor__last_name']
    list_select_related = ('professor',)
