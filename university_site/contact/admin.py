from django.contrib import admin
from .models import ContactMessage, Alumni


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'email', 'subject', 'status', 'created_at']
    list_filter = ['status', 'subject']
    list_editable = ['status']
    search_fields = ['full_name', 'email', 'message']
    readonly_fields = ['full_name', 'email', 'phone', 'subject', 'message', 'ip_address', 'created_at']
    date_hierarchy = 'created_at'
    fieldsets = (
        ('پیام', {'fields': ('full_name', 'email', 'phone', 'subject', 'message', 'ip_address', 'created_at')}),
        ('پاسخ', {'fields': ('status', 'reply')}),
    )


@admin.register(Alumni)
class AlumniAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'graduation_year', 'major', 'degree', 'is_featured']
    list_filter = ['graduation_year', 'is_featured']
    list_editable = ['is_featured']
    search_fields = ['full_name', 'major']
