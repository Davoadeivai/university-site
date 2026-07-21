from django.contrib import admin, messages
from django.utils.html import format_html
from .models import (
    AdmissionInfo, Application,
    TuitionStructure, TuitionDiscount, StudentPayment, AdmissionOTP,
)


# ─────────────────────────────────────────────
#  اطلاعات پذیرش
# ─────────────────────────────────────────────
@admin.register(AdmissionInfo)
class AdmissionInfoAdmin(admin.ModelAdmin):
    list_display = ['get_degree', 'title', 'deadline', 'capacity', 'is_open_badge', 'is_active']
    list_editable = ['is_active']
    list_filter = ['degree', 'is_active']
    search_fields = ['title', 'description']
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('degree', 'title', 'description', 'is_active', 'deadline', 'capacity')
        }),
        ('محتوا', {
            'fields': ('requirements', 'documents_required', 'tuition_info', 'registration_link')
        }),
    )

    @admin.display(description='مقطع')
    def get_degree(self, obj):
        return obj.get_degree_display()

    @admin.display(description='ثبت‌نام باز است؟', boolean=True)
    def is_open_badge(self, obj):
        return obj.is_open


class StudentPaymentInline(admin.TabularInline):
    model = StudentPayment
    extra = 0
    fields = [
        'installment_no', 'amount', 'due_date', 'status',
        'paid_at', 'receipt', 'confirmed_by', 'notes',
    ]
    readonly_fields = ['paid_at']
    verbose_name = 'قسط شهریه'
    verbose_name_plural = 'اقساط شهریه این متقاضی'
    show_change_link = True


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = [
        'tracking_code', 'full_name', 'national_id', 'phone',
        'degree_fa', 'desired_major', 'status_badge',
        'phone_verified', 'docs_summary', 'created_at',
    ]
    list_filter = [
        'status', 'degree', 'gender', 'shift', 'phone_verified',
        'desired_major', 'created_at',
    ]
    list_editable = []  # وضعیت فقط از فرم/اکشن تا اشتباه انبوه کمتر شود
    search_fields = [
        'tracking_code', 'national_id', 'first_name', 'last_name',
        'phone', 'email', 'father_name',
        'desired_major__name', 'desired_major2__name',
    ]
    readonly_fields = [
        'tracking_code', 'created_at', 'updated_at',
        'doc_national_id_preview', 'doc_prev_degree_preview',
        'doc_photo_preview', 'doc_military_preview',
    ]
    autocomplete_fields = ['desired_major', 'desired_major2']
    inlines = [StudentPaymentInline]
    date_hierarchy = 'created_at'
    list_per_page = 25
    list_select_related = ('desired_major', 'desired_major2')
    ordering = ['-created_at']
    save_on_top = True
    actions = [
        'action_mark_reviewing',
        'action_mark_accepted',
        'action_mark_rejected',
        'action_mark_interview',
        'action_mark_incomplete',
        'action_mark_waiting',
    ]

    fieldsets = (
        ('کد رهگیری و وضعیت', {
            'fields': (
                ('tracking_code', 'status'),
                ('phone_verified', 'agreed_terms'),
                ('created_at', 'updated_at'),
            )
        }),
        ('اطلاعات هویتی', {
            'fields': (
                ('first_name', 'last_name', 'father_name'),
                ('national_id', 'birth_date', 'gender'),
                'military',
            )
        }),
        ('اطلاعات تماس', {
            'fields': (
                ('phone', 'phone_emergency'),
                'email',
                'address',
                'postal_code',
            )
        }),
        ('سوابق تحصیلی', {
            'fields': (
                ('prev_degree', 'prev_major'),
                ('prev_school', 'prev_grad_year'),
                'gpa',
            )
        }),
        ('رشته و مقطع درخواستی', {
            'fields': (
                'degree',
                ('desired_major', 'desired_major2'),
                'shift',
            )
        }),
        ('مدارک آپلودشده', {
            'fields': (
                ('doc_national_id', 'doc_national_id_preview'),
                ('doc_prev_degree', 'doc_prev_degree_preview'),
                ('doc_photo', 'doc_photo_preview'),
                ('doc_military', 'doc_military_preview'),
            )
        }),
        ('سایر اطلاعات متقاضی', {
            'fields': ('know_from', 'special_needs'),
        }),
        ('بررسی کارشناس پذیرش', {
            'fields': (
                'admin_notes',
                'reject_reason',
                'interview_date',
            ),
            'description': 'یادداشت داخلی، دلیل رد و زمان مصاحبه برای پیگیری پذیرش.',
        }),
    )

    # ── ستون‌های لیست ──
    @admin.display(description='نام متقاضی', ordering='last_name')
    def full_name(self, obj):
        return f'{obj.first_name} {obj.last_name}'

    @admin.display(description='مقطع', ordering='degree')
    def degree_fa(self, obj):
        return obj.get_degree_display()

    @admin.display(description='وضعیت')
    def status_badge(self, obj):
        colors = {
            'pending': '#f59e0b',
            'reviewing': '#3b82f6',
            'incomplete': '#a855f7',
            'interview': '#06b6d4',
            'accepted': '#16a34a',
            'rejected': '#dc2626',
            'waiting': '#64748b',
        }
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 10px;'
            'border-radius:10px;font-size:12px;white-space:nowrap;">{}</span>',
            colors.get(obj.status, '#64748b'),
            obj.get_status_display(),
        )

    @admin.display(description='مدارک')
    def docs_summary(self, obj):
        items = [
            ('ملی', bool(obj.doc_national_id)),
            ('مدرک', bool(obj.doc_prev_degree)),
            ('عکس', bool(obj.doc_photo)),
            ('نظام', bool(obj.doc_military)),
        ]
        parts = []
        for label, ok in items:
            color = '#16a34a' if ok else '#cbd5e1'
            parts.append(
                f'<span style="color:{color};font-size:11px;margin-left:4px;">{label}</span>'
            )
        return format_html(''.join(parts))

    def _img_preview(self, field_file, empty='فایلی آپلود نشده'):
        if not field_file:
            return empty
        try:
            url = field_file.url
        except ValueError:
            return empty
        return format_html(
            '<a href="{0}" target="_blank" rel="noopener">'
            '<img src="{0}" style="max-height:120px;max-width:180px;'
            'border-radius:8px;border:1px solid #e2e8f0;" alt="مدرک" />'
            '</a>',
            url,
        )

    @admin.display(description='پیش‌نمایش کارت ملی')
    def doc_national_id_preview(self, obj):
        return self._img_preview(obj.doc_national_id)

    @admin.display(description='پیش‌نمایش مدرک تحصیلی')
    def doc_prev_degree_preview(self, obj):
        return self._img_preview(obj.doc_prev_degree)

    @admin.display(description='پیش‌نمایش عکس پرسنلی')
    def doc_photo_preview(self, obj):
        return self._img_preview(obj.doc_photo)

    @admin.display(description='پیش‌نمایش نظام وظیفه')
    def doc_military_preview(self, obj):
        return self._img_preview(obj.doc_military)

    # ── اکشن‌های گروهی (فارسی) ──
    def _bulk_status(self, request, queryset, status, label):
        # save() تکی تا سیگنال پیامک وضعیت پذیرش اجرا شود
        updated = 0
        for app in queryset:
            if app.status == status:
                continue
            app.status = status
            app.save(update_fields=['status'])
            updated += 1
        self.message_user(
            request,
            f'{updated} درخواست به وضعیت «{label}» تغییر کرد.',
            messages.SUCCESS,
        )

    @admin.action(description='تغییر وضعیت به: در حال بررسی')
    def action_mark_reviewing(self, request, queryset):
        self._bulk_status(request, queryset, 'reviewing', 'در حال بررسی')

    @admin.action(description='تغییر وضعیت به: پذیرفته شده')
    def action_mark_accepted(self, request, queryset):
        self._bulk_status(request, queryset, 'accepted', 'پذیرفته شده')

    @admin.action(description='تغییر وضعیت به: رد شده')
    def action_mark_rejected(self, request, queryset):
        self._bulk_status(request, queryset, 'rejected', 'رد شده')

    @admin.action(description='تغییر وضعیت به: دعوت به مصاحبه')
    def action_mark_interview(self, request, queryset):
        self._bulk_status(request, queryset, 'interview', 'دعوت به مصاحبه')

    @admin.action(description='تغییر وضعیت به: نیاز به تکمیل مدارک')
    def action_mark_incomplete(self, request, queryset):
        self._bulk_status(request, queryset, 'incomplete', 'نیاز به تکمیل مدارک')

    @admin.action(description='تغییر وضعیت به: لیست انتظار')
    def action_mark_waiting(self, request, queryset):
        self._bulk_status(request, queryset, 'waiting', 'لیست انتظار')


@admin.register(TuitionStructure)
class TuitionStructureAdmin(admin.ModelAdmin):
    list_display = [
        'major', 'degree_display', 'academic_year', 'fixed_fee_fmt',
        'theory_fee_fmt', 'practical_fee_fmt', 'is_active',
    ]
    list_filter = ['major__degree', 'academic_year', 'is_active', 'major__group']
    list_editable = ['is_active']
    search_fields = ['major__name', 'academic_year']
    autocomplete_fields = ['major']
    fieldsets = (
        ('اطلاعات پایه', {
            'fields': ('major', 'academic_year', 'is_active')
        }),
        ('شهریه اصلی', {
            'fields': (
                ('fixed_fee', 'theory_fee'),
                ('practical_fee', 'lab_fee'),
            )
        }),
        ('هزینه‌های جانبی', {
            'fields': (
                ('registration_fee', 'insurance_fee'),
                ('card_fee', 'dorm_fee'),
            )
        }),
        ('توضیحات', {'fields': ('notes',)}),
    )

    def _fmt(self, v):
        return f'{v:,} تومان'

    @admin.display(description='مقطع', ordering='major__degree')
    def degree_display(self, obj):
        return obj.major.get_degree_display()

    @admin.display(description='شهریه ثابت')
    def fixed_fee_fmt(self, obj):
        return self._fmt(obj.fixed_fee)

    @admin.display(description='هر واحد نظری')
    def theory_fee_fmt(self, obj):
        return self._fmt(obj.theory_fee)

    @admin.display(description='هر واحد عملی')
    def practical_fee_fmt(self, obj):
        return self._fmt(obj.practical_fee)


@admin.register(TuitionDiscount)
class TuitionDiscountAdmin(admin.ModelAdmin):
    list_display = ['title', 'discount_type', 'percent', 'is_active']
    list_editable = ['is_active']
    list_filter = ['discount_type', 'is_active']
    search_fields = ['title', 'description']
    fieldsets = (
        ('اطلاعات تخفیف', {
            'fields': ('discount_type', 'title', 'percent', 'is_active', 'description')
        }),
    )


@admin.register(StudentPayment)
class StudentPaymentAdmin(admin.ModelAdmin):
    list_display = [
        'application', 'installment_no', 'amount_fmt',
        'due_date', 'status_badge', 'confirmed_by',
    ]
    list_filter = ['status', 'due_date']
    search_fields = [
        'application__tracking_code', 'application__first_name',
        'application__last_name', 'application__national_id',
    ]
    readonly_fields = ['paid_at']
    autocomplete_fields = ['application']
    fieldsets = (
        ('متقاضی و قسط', {
            'fields': ('application', 'installment_no', 'amount', 'due_date', 'status')
        }),
        ('پرداخت و تأیید', {
            'fields': ('paid_at', 'receipt', 'confirmed_by', 'notes')
        }),
    )

    def _fmt(self, v):
        return f'{v:,} تومان'

    @admin.display(description='مبلغ')
    def amount_fmt(self, obj):
        return self._fmt(obj.amount)

    @admin.display(description='وضعیت')
    def status_badge(self, obj):
        colors = {
            'paid': '#16a34a', 'pending': '#f59e0b',
            'overdue': '#dc2626', 'waived': '#64748b',
        }
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:10px;font-size:12px;">{}</span>',
            colors.get(obj.status, '#64748b'),
            obj.get_status_display(),
        )


@admin.register(AdmissionOTP)
class AdmissionOTPAdmin(admin.ModelAdmin):
    list_display = ['phone', 'created_at', 'expires_at', 'is_used', 'attempts']
    list_filter = ['is_used', 'created_at']
    search_fields = ['phone']
    readonly_fields = ['phone', 'code', 'created_at', 'expires_at', 'attempts', 'is_used']
    fieldsets = (
        ('کد تأیید موبایل', {
            'fields': ('phone', 'code', 'is_used', 'attempts', 'created_at', 'expires_at'),
            'description': 'کدها فقط برای پیگیری امنیتی نمایش داده می‌شوند و قابل ویرایش نیستند.',
        }),
    )
