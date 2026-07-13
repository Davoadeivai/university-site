from django.contrib import admin
from .models import UserProfile, Announcement


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'student_id', 'department']
    list_filter = ['role']
    search_fields = ['user__username', 'user__first_name', 'student_id']


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ['title', 'target', 'is_urgent', 'is_active', 'created_at']
    list_filter = ['target', 'is_urgent', 'is_active']
    list_editable = ['is_urgent', 'is_active']
    search_fields = ['title', 'content']
