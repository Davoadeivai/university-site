from django.contrib import admin
from .models import ResearchProject, Journal, Thesis, Conference, IndustryPartnership


@admin.register(ResearchProject)
class ResearchProjectAdmin(admin.ModelAdmin):
    list_display = ['title', 'researcher', 'status', 'is_featured', 'start_date']
    list_filter = ['status', 'is_featured']
    list_editable = ['is_featured']
    search_fields = ['title', 'researcher']


@admin.register(Journal)
class JournalAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'issn', 'order', 'is_active']
    list_filter = ['category', 'is_active']
    list_editable = ['order', 'is_active']
    prepopulated_fields = {'slug': ('title',)}
    search_fields = ['title', 'description']


@admin.register(Thesis)
class ThesisAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'supervisor', 'degree', 'year']
    list_filter = ['degree', 'year']
    search_fields = ['title', 'author', 'supervisor']


@admin.register(Conference)
class ConferenceAdmin(admin.ModelAdmin):
    list_display = ['title', 'date', 'location', 'is_upcoming']
    list_filter = ['is_upcoming']
    list_editable = ['is_upcoming']


@admin.register(IndustryPartnership)
class IndustryPartnershipAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'partnership_type', 'is_active']
    list_editable = ['is_active']
