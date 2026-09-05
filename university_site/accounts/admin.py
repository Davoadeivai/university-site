from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.html import format_html

from core.admin_jalali import JalaliAdminMixin

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

    def _delete_block(self, request, obj):
        """چرا این کاربر حذف نمی‌شود — یا خالی، اگر می‌شود.

        هر سه دلیل، حذفی را می‌گیرند که برگشت ندارد: بیرون‌انداختن
        خودِ کاربر از حسابش، برداشتن مدیری که اجازه‌اش را نداری، و
        پاک‌کردن آخرین مدیر کل که یعنی قفل‌شدن همیشگی پنل.
        """
        if obj is None:
            return ''
        if obj.pk == request.user.pk:
            return 'این حساب خودِ شماست؛ با حذفش از پنل بیرون می‌افتید.'
        if obj.is_superuser and not request.user.is_superuser:
            return 'این کاربر مدیر کل است و فقط مدیر کل می‌تواند حذفش کند.'
        if obj.is_superuser and User.objects.filter(
                is_superuser=True, is_active=True).exclude(pk=obj.pk).count() == 0:
            return 'تنها مدیر کل سایت است؛ با حذفش هیچ‌کس به پنل راه ندارد.'
        return ''

    def has_delete_permission(self, request, obj=None):
        if self._delete_block(request, obj):
            return False
        return super().has_delete_permission(request, obj)

    @admin.display(description='حذف')
    def delete_button(self, obj):
        """دکمه فقط وقتی دیده شود که واقعاً کار کند.

        پیش از این برای هر ردیف رندر می‌شد — حتی برای حسابی که اجازهٔ
        حذف نداشت. کلیک روی آن یک صفحهٔ ۴۰۳ می‌آورد و کاربر فقط
        می‌دید که «نمی‌شود»، بی‌آنکه بداند چرا.
        """
        request = getattr(self, '_request', None)
        reason = self._delete_block(request, obj) if request else ''
        if not reason and request and not super().has_delete_permission(
                request, obj):
            reason = 'حساب شما اجازهٔ حذف کاربر ندارد.'
        if reason:
            return format_html(
                '<span style="color:#9a9a9a;cursor:help;" title="{}">—</span>',
                reason)
        url = reverse('admin:auth_user_delete', args=[obj.pk])
        return format_html(
            '<a class="btn btn-sm btn-danger" href="{}" title="حذف این کاربر">حذف</a>',
            url,
        )

    def changelist_view(self, request, extra_context=None):
        # ‎delete_button‎ به خودِ درخواست نیاز دارد تا بداند این
        # بیننده اجازهٔ حذف دارد یا نه؛ ستون‌ها آن را نمی‌گیرند.
        self._request = request
        return super().changelist_view(request, extra_context)

    @admin.action(description='حذف کاربران انتخاب‌شده')
    def delete_selected_users(self, request, queryset):
        from django.contrib import messages
        from django.contrib.admin.actions import delete_selected

        blocked = [(user, self._delete_block(request, user))
                   for user in queryset]
        kept = [row for row in blocked if row[1]]
        for user, reason in kept:
            messages.warning(
                request, '«%s» حذف نشد — %s' % (user.get_username(), reason))
        allowed = queryset.exclude(pk__in=[user.pk for user, _ in kept])
        if not allowed:
            return None
        return delete_selected(self, request, allowed)

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop('delete_selected', None)
        return actions


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'role', 'academic_status', 'national_id', 'phone',
        'student_id', 'major', 'department',
    ]
    list_filter = ['role', 'academic_status', 'major__degree', 'major', 'department']
    search_fields = [
        'user__username', 'user__first_name', 'user__last_name',
        'student_id', 'national_id', 'phone', 'major__name',
    ]
    autocomplete_fields = ['user', 'major']
    list_select_related = ('user', 'major')
    readonly_fields = ['status_changed_at']
    fieldsets = (
        ('کاربر و نقش', {
            'fields': ('user', 'role', 'avatar', 'photo_hijab_confirmed')
        }),
        ('وضعیت تحصیلی', {
            'fields': ('academic_status', 'status_changed_at', 'status_note'),
            'description': 'اخراج و مرخصی اجباری فقط از این بخش. فارغ‌التحصیلی/انصراف معمولاً از درخواست دانشجو.',
        }),
        ('اطلاعات هویتی', {
            'fields': (
                'national_id', 'father_name', 'birth_date', 'gender', 'military',
                'student_id', 'major', 'department',
            )
        }),
        ('تماس و سکونت', {
            'fields': ('phone', 'phone_emergency', 'province', 'city', 'address', 'postal_code')
        }),
        ('سوابق تحصیلی', {
            'fields': ('prev_degree', 'prev_major', 'prev_school', 'prev_grad_year', 'gpa', 'bio')
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        """
        نقش فقط توسط superuser قابل تغییر است.

        گروه «مدیر دانشگاه» مجوز change_userprofile دارد؛ اگر این فیلد باز بماند
        هر عضو آن گروه می‌تواند نقش خودش را روی «admin» بگذارد. فرم افزودن هم امن
        است چون UserProfile.role مقدار پیش‌فرض 'student' دارد.
        """
        ro = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser and 'role' not in ro:
            ro.append('role')
        return ro

    def save_model(self, request, obj, form, change):
        from django.utils import timezone
        if change and 'academic_status' in form.changed_data:
            obj.status_changed_at = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(Announcement)
class AnnouncementAdmin(JalaliAdminMixin, admin.ModelAdmin):
    list_display = ['title', 'target', 'is_urgent', 'is_active', 'created_jalali', 'expires_jalali']
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
class OTPCodeAdmin(JalaliAdminMixin, admin.ModelAdmin):
    list_display = ['user', 'created_jalali', 'expires_jalali', 'is_used']
    list_filter = ['is_used', 'created_at']
    search_fields = ['user__username', 'user__first_name', 'user__last_name']
    list_select_related = ('user',)
    readonly_fields = ['user', 'created_at', 'expires_at', 'is_used']
    fieldsets = (
        ('کد تأیید بازیابی رمز', {
            'fields': ('user', 'is_used', 'created_at', 'expires_at'),
            'description': (
                'خودِ کد نمایش داده نمی‌شود؛ نمایش آن یعنی دارندهٔ دسترسی می‌تواند '
                'کد فعال هر کاربر را بخواند و وارد حسابش شود. زمان ایجاد، انقضا و '
                'وضعیت مصرف برای پیگیری امنیتی کافی است.'
            ),
        }),
    )
