from django.contrib import admin

from core.admin_jalali import JalaliAdminMixin
from core.jalali import format_jalali_datetime
from .models import ContactMessage, Alumni


@admin.register(ContactMessage)
class ContactMessageAdmin(JalaliAdminMixin, admin.ModelAdmin):
    list_display = ['full_name', 'email', 'subject', 'status', 'created_jalali']
    list_filter = ['status', 'subject']
    list_editable = ['status']
    search_fields = ['full_name', 'email', 'message']
    readonly_fields = ['full_name', 'email', 'phone', 'subject', 'message', 'ip_address', 'created_at_jalali_ro']
    fieldsets = (
        ('پیام', {'fields': ('full_name', 'email', 'phone', 'subject', 'message', 'ip_address', 'created_at_jalali_ro')}),
        ('پاسخ', {'fields': ('status', 'reply')}),
    )

    @admin.display(description='تاریخ ثبت')
    def created_at_jalali_ro(self, obj):
        return format_jalali_datetime(obj.created_at)


@admin.register(Alumni)
class AlumniAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'graduation_year', 'major', 'degree', 'is_featured']
    list_filter = ['graduation_year', 'is_featured']
    list_editable = ['is_featured']
    search_fields = ['full_name', 'major']
