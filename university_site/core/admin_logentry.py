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
        """ردیف لاگ مستقیم پاک نمی‌شود، ولی جلوی حذف کاربر را هم نگیرد.

        این متد دو جای کاملاً متفاوت صدا زده می‌شود و «False» برای هر
        دو، یک ایراد جدی می‌ساخت: هنگام حذف یک کاربر، جنگو برای هر
        مدلی که به او وصل است همین را می‌پرسد، و چون لاگ‌های او با
        CASCADE پاک می‌شوند، پاسخ منفی یعنی «حساب شما دسترسی حذف
        اشیای از نوع مورد اتفاقات را ندارد» — برای همه، حتی مدیر کل.
        نتیجه‌اش این بود که هیچ کاربری که یک بار در پنل کاری کرده
        باشد، دیگر قابل حذف نبود.

        پس اجازه فقط در همان مسیرِ آبشاری باز است (obj داده می‌شود) و
        فقط برای مدیر کل؛ حذف مستقیمِ خودِ ردیف لاگ را `delete_view`
        پایین می‌بندد.
        """
        return obj is not None and request.user.is_superuser

    def delete_view(self, request, object_id, extra_context=None):
        """تاریخچه دست‌کاری نمی‌شود — حتی به دست مدیر کل."""
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied

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
