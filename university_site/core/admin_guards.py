"""گاردهای دسترسی برای ویوهای سفارشی ادمین.

`AdminSite.admin_view()` تنها `request.user.is_active and request.user.is_staff`
را بررسی می‌کند و **مجوز سطح-مدل را چک نمی‌کند**. بنابراین هر ویو سفارشی که
داده‌ای فراتر از منوی کاربر برمی‌گرداند (خروجی اکسل/ورد، گزارش، چاپ) باید
گارد صریح خودش را داشته باشد؛ وگرنه هر کاربر staff — حتی بدون هیچ مجوزی روی
آن مدل و حتی وقتی مدل در منوی او دیده نمی‌شود — می‌تواند مستقیماً آدرس ویو را
باز کند و داده را بگیرد.
"""
from __future__ import annotations

from functools import wraps

from django.core.exceptions import PermissionDenied


def require_model_view_permission(view):
    """ویو سفارشی یک ModelAdmin را به مجوز `view` همان مدل مقید می‌کند.

    روی متدهای ModelAdmin استفاده می‌شود:

        @require_model_view_permission
        def export_excel_view(self, request):
            ...
    """

    @wraps(view)
    def wrapper(self, request, *args, **kwargs):
        if not self.has_view_permission(request):
            raise PermissionDenied
        return view(self, request, *args, **kwargs)

    return wrapper
