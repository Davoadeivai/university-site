from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.html import format_html

from .models import UserProfile, Announcement, OTPCode


# بازنویسی ادمین کاربران: دکمه حذف واضح + اکشن گروهی فارسی
if admin.site.is_registered(User):
    admin.site.unregister(User)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = (
        'username', 'email', 'first_name', 'last_name',
        'is_staff', 'is_active', 'delete_button',
    )
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    actions = ['delete_selected_users']
    ordering = ('username',)

    @admin.display(description='حذف')
    def delete_button(self, obj):
        url = reverse('admin:auth_user_delete', args=[obj.pk])
        return format_html(
            '<a class="btn btn-sm btn-danger" href="{}" title="حذف این کاربر">حذف</a>',
            url,
        )

    @admin.action(description='حذف کاربران انتخاب‌شده')
    def delete_selected_users(self, request, queryset):
        from django.contrib.admin.actions import delete_selected
        return delete_selected(self, request, queryset)

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop('delete_selected', None)
        return actions


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'national_id', 'phone', 'student_id', 'major', 'department']
    list_filter = ['role', 'major__degree', 'major', 'department']
    search_fields = [
        'user__username', 'user__first_name', 'user__last_name',
        'student_id', 'national_id', 'phone', 'major__name',
    ]
    autocomplete_fields = ['user', 'major']
    fieldsets = (
        ('کاربر و نقش', {
            'fields': ('user', 'role', 'avatar')
        }),
        ('اطلاعات هویتی و تماس', {
            'fields': ('national_id', 'phone', 'birth_date', 'student_id', 'major', 'department')
        }),
        ('سایر', {
            'fields': ('bio',)
        }),
    )


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ['title', 'target', 'is_urgent', 'is_active', 'created_at', 'expires_at']
    list_filter = ['target', 'is_urgent', 'is_active']
    list_editable = ['is_urgent', 'is_active']
    search_fields = ['title', 'content']
    fieldsets = (
        ('اطلاعیه', {
            'fields': ('title', 'content', 'target', 'file')
        }),
        ('نمایش', {
            'fields': ('is_active', 'is_urgent', 'expires_at')
        }),
    )


@admin.register(OTPCode)
class OTPCodeAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at', 'expires_at', 'is_used']
    list_filter = ['is_used', 'created_at']
    search_fields = ['user__username', 'user__first_name', 'user__last_name']
    readonly_fields = ['user', 'code', 'created_at', 'expires_at', 'is_used']
    fieldsets = (
        ('کد تأیید بازیابی رمز', {
            'fields': ('user', 'code', 'is_used', 'created_at', 'expires_at'),
            'description': 'کدها فقط برای پیگیری امنیتی نمایش داده می‌شوند و قابل ویرایش نیستند.',
        }),
    )
