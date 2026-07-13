from django.contrib import admin
from .models import Professor, Publication


class PublicationInline(admin.TabularInline):
    model = Publication
    extra = 0
    fields = ['title', 'pub_type', 'year', 'journal_conference']


@admin.register(Professor)
class ProfessorAdmin(admin.ModelAdmin):
    list_display = ['get_full_name', 'department', 'rank', 'status', 'is_active', 'order']
    list_filter = ['rank', 'status', 'department', 'is_active']
    list_editable = ['order', 'is_active']
    search_fields = ['first_name', 'last_name', 'email']
    inlines = [PublicationInline]
    fieldsets = (
        ('اطلاعات اصلی', {'fields': ('first_name', 'last_name', 'slug', 'photo', 'rank', 'status', 'department')}),
        ('اطلاعات تماس', {'fields': ('email', 'phone', 'office', 'office_hours')}),
        ('علمی', {'fields': ('bio', 'education', 'specialization', 'research_interests')}),
        ('لینک‌ها', {'fields': ('personal_website', 'google_scholar', 'linkedin', 'researchgate')}),
        ('وضعیت', {'fields': ('is_active', 'order')}),
    )


@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    list_display = ['title', 'professor', 'pub_type', 'year']
    list_filter = ['pub_type', 'year']
    search_fields = ['title', 'professor__last_name']
