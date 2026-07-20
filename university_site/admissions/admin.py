from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import (
    AdmissionInfo, Application,
    TuitionStructure, TuitionDiscount, StudentPayment, AdmissionOTP,
)


# ─────────────────────────────────────────────
#  اطلاعات پذیرش
# ─────────────────────────────────────────────
@admin.register(AdmissionInfo)
class AdmissionInfoAdmin(admin.ModelAdmin):
    list_display  = ['get_degree', 'title', 'deadline', 'capacity', 'is_open_badge', 'is_active']
    list_editable = ['is_active']
    list_filter   = ['degree', 'is_active']
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

    @admin.display(description='وضعیت ثبت‌نام', boolean=True)
    def is_open_badge(self, obj):
        return obj.is_open


class StudentPaymentInline(admin.TabularInline):
    model = StudentPayment
    extra = 0
    fields = ['installment_no', 'amount', 'due_date', 'status', 'confirmed_by']


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = [
        'tracking_code', 'full_name', 'national_id', 'phone',
        'desired_major', 'degree', 'status', 'created_at',
    ]
    list_filter = ['status', 'degree', 'created_at', 'desired_major']
    list_editable = ['status']
    search_fields = ['tracking_code', 'national_id', 'first_name', 'last_name', 'phone',
                     'desired_major__name']
    readonly_fields = ['tracking_code', 'created_at', 'updated_at']
    autocomplete_fields = ['desired_major', 'desired_major2']
    inlines = [StudentPaymentInline]
    date_hierarchy = 'created_at'

    @admin.display(description='نام')
    def full_name(self, obj):
        return f'{obj.first_name} {obj.last_name}'


@admin.register(TuitionStructure)
class TuitionStructureAdmin(admin.ModelAdmin):
    list_display  = ['major', 'degree_display', 'academic_year', 'fixed_fee_fmt',
                     'theory_fee_fmt', 'practical_fee_fmt', 'is_active']
    list_filter   = ['major__degree', 'academic_year', 'is_active', 'major__group']
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
        return f"{v:,} ت"

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
    list_display  = ['title', 'discount_type', 'percent', 'is_active']
    list_editable = ['is_active']
    list_filter   = ['discount_type', 'is_active']


@admin.register(StudentPayment)
class StudentPaymentAdmin(admin.ModelAdmin):
    list_display  = ['application', 'installment_no', 'amount_fmt',
                     'due_date', 'status_badge', 'confirmed_by']
    list_filter   = ['status']
    search_fields = ['application__tracking_code', 'application__first_name',
                     'application__last_name', 'application__national_id']
    readonly_fields = ['paid_at']

    def _fmt(self, v):
        return f"{v:,} ت"

    @admin.display(description='مبلغ')
    def amount_fmt(self, obj):
        return self._fmt(obj.amount)

    @admin.display(description='وضعیت')
    def status_badge(self, obj):
        colors = {
            'paid': '#16a34a', 'pending': '#f59e0b',
            'overdue': '#dc2626', 'waived': '#64748b',
        }
        c = colors.get(obj.status, '#64748b')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:10px;font-size:12px;">{}</span>',
            c, obj.get_status_display()
        )


@admin.register(AdmissionOTP)
class AdmissionOTPAdmin(admin.ModelAdmin):
    list_display = ['phone', 'created_at', 'expires_at', 'is_used', 'attempts']
    list_filter  = ['is_used']
    readonly_fields = ['phone', 'code', 'created_at', 'expires_at', 'attempts']
    # کد در لیست نمایش داده نمی‌شود تا امنیت بیشتر شود
