"""لاگ فعالیت ادمین — «چه کسی، چه چیزی را، کی تغییر داد».

روی سامانه‌ای که پول جابه‌جا می‌کند و نقش کاربران را عوض می‌کند، این تاریخچه
باید قابل جستجو باشد. جنگو آن را در `LogEntry` ثبت می‌کند ولی به‌صورت
پیش‌فرض در ادمین نمایش نمی‌دهد.

فقط‌خواندنی است: افزودن/ویرایش/حذف غیرفعال‌اند تا تاریخچه دست‌کاری نشود.
"""
from __future__ import annotations

from django.contrib import admin
from django.contrib.admin.models import ADDITION, CHANGE, DELETION, LogEntry
from django.utils.html import format_html

from core.admin_jalali import JalaliAdminMixin


@admin.register(LogEntry)
class LogEntryAdmin(JalaliAdminMixin, admin.ModelAdmin):
    list_display = [
        'action_time_jalali', 'user', 'action_badge',
        'content_type', 'object_repr', 'change_message_short',
    ]
    list_filter = ['action_flag', 'content_type', 'action_time']
    search_fields = ['object_repr', 'change_message', 'user__username']
    list_select_related = ('user', 'content_type')
    date_hierarchy = None  # روی MySQL بدون جداول timezone خطا می‌دهد
    ordering = ['-action_time']
    list_per_page = 60

    # تاریخچه باید تغییرناپذیر بماند
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        # فقط superuser — لاگ شامل نام رکوردهای حساس است
        return request.user.is_superuser

    @admin.display(description='زمان', ordering='action_time')
    def action_time_jalali(self, obj):
        from core.jalali import format_jalali_datetime
        return format_jalali_datetime(obj.action_time) or '—'

    @admin.display(description='عملیات', ordering='action_flag')
    def action_badge(self, obj):
        mapping = {
            ADDITION: ('افزودن', '#16a34a'),
            CHANGE: ('ویرایش', '#2563eb'),
            DELETION: ('حذف', '#dc2626'),
        }
        label, color = mapping.get(obj.action_flag, ('نامشخص', '#64748b'))
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 9px;'
            'border-radius:10px;font-size:12px;white-space:nowrap;">{}</span>',
            color, label,
        )

    @admin.display(description='توضیح تغییر')
    def change_message_short(self, obj):
        msg = obj.get_change_message() or '—'
        return msg if len(msg) <= 90 else msg[:89] + '…'
