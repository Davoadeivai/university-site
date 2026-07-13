from django.contrib import admin
from django.utils.html import format_html
from .models import AdmissionInfo, Application, Tuition


@admin.register(AdmissionInfo)
class AdmissionInfoAdmin(admin.ModelAdmin):
    list_display = ['degree_badge', 'title', 'deadline', 'active_badge', 'is_active']
    list_editable = ['is_active']
    list_filter = ['degree', 'is_active']
    search_fields = ['title', 'description']
    list_per_page = 20

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('degree', 'title', 'is_active', 'deadline'),
            'description': 'اطلاعات پایه مقطع تحصیلی را وارد کنید',
        }),
        ('توضیحات و شرایط', {
            'fields': ('description', 'requirements'),
            'description': 'توضیحات کامل و شرایط پذیرش را وارد کنید',
        }),
        ('اطلاعات تکمیلی', {
            'fields': ('tuition_info', 'documents_required', 'registration_link'),
            'description': 'اطلاعات شهریه، مدارک لازم و لینک ثبت‌نام',
        }),
    )

    def degree_badge(self, obj):
        colors = {
            'associate': '#6366f1',
            'bachelor': '#0ea5e9',
            'master': '#10b981',
            'phd': '#f59e0b',
        }
        color = colors.get(obj.degree, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600">{}</span>',
            color, obj.get_degree_display()
        )
    degree_badge.short_description = 'مقطع'

    def active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="background:#10b981;color:#fff;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600">✓ فعال</span>')
        return format_html('<span style="background:#ef4444;color:#fff;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600">✗ غیرفعال</span>')
    active_badge.short_description = 'وضعیت'
    active_badge.admin_order_field = 'is_active'


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ['get_full_name', 'phone', 'degree_badge', 'desired_major', 'status_badge', 'status', 'created_at']
    list_filter = ['status', 'degree']
    list_editable = ['status']
    search_fields = ['first_name', 'last_name', 'national_id', 'phone']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    list_per_page = 25

    fieldsets = (
        ('اطلاعات شخصی', {
            'fields': (('first_name', 'last_name'), ('national_id', 'birth_date'), ('phone', 'email')),
            'description': 'اطلاعات هویتی و تماس متقاضی',
        }),
        ('اطلاعات تحصیلی', {
            'fields': ('degree', 'desired_major', ('gpa', 'previous_degree')),
            'description': 'مقطع و رشته درخواستی متقاضی',
        }),
        ('آدرس و توضیحات', {
            'fields': ('address', 'notes'),
            'description': 'آدرس محل سکونت و یادداشت‌های بررسی',
        }),
        ('وضعیت درخواست', {
            'fields': ('status', 'created_at'),
            'description': 'وضعیت فعلی درخواست پذیرش',
        }),
    )

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    get_full_name.short_description = 'نام متقاضی'

    def degree_badge(self, obj):
        colors = {
            'associate': '#6366f1',
            'bachelor': '#0ea5e9',
            'master': '#10b981',
            'phd': '#f59e0b',
        }
        color = colors.get(obj.degree, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600">{}</span>',
            color, obj.get_degree_display()
        )
    degree_badge.short_description = 'مقطع'

    def status_badge(self, obj):
        styles = {
            'pending':   ('⏳', '#f59e0b'),
            'reviewing': ('🔍', '#3b82f6'),
            'accepted':  ('✅', '#10b981'),
            'rejected':  ('❌', '#ef4444'),
            'waiting':   ('⏸', '#8b5cf6'),
        }
        icon, color = styles.get(obj.status, ('?', '#6b7280'))
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600">{} {}</span>',
            color, icon, obj.get_status_display()
        )
    status_badge.short_description = 'وضعیت'
    status_badge.admin_order_field = 'status'


@admin.register(Tuition)
class TuitionAdmin(admin.ModelAdmin):
    list_display = ['major', 'degree', 'base_fee_display', 'per_credit_fee_display', 'academic_year']
    list_filter = ['academic_year', 'degree']
    search_fields = ['major', 'academic_year']
    list_per_page = 20

    fieldsets = (
        ('مشخصات رشته', {
            'fields': ('major', 'degree', 'academic_year'),
            'description': 'رشته تحصیلی، مقطع و سال تحصیلی',
        }),
        ('اطلاعات شهریه', {
            'fields': ('base_fee', 'per_credit_fee', 'notes'),
            'description': 'مقادیر شهریه به تومان',
        }),
    )

    def base_fee_display(self, obj):
        return format_html('<span style="font-weight:600;color:#10b981">{:,} تومان</span>', obj.base_fee)
    base_fee_display.short_description = 'شهریه پایه'

    def per_credit_fee_display(self, obj):
        return format_html('<span style="font-weight:600;color:#3b82f6">{:,} تومان</span>', obj.per_credit_fee)
    per_credit_fee_display.short_description = 'شهریه هر واحد'
