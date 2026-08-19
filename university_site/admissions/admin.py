from django.contrib import admin, messages
from django.db.models import Count
from django.urls import path, reverse
from django.utils.html import format_html, mark_safe
from django.utils.translation import gettext_lazy as _

from core.admin_guards import require_model_view_permission
from core.admin_jalali import JalaliAdminMixin
from core.jalali import jalali_year_range

from .application_export import excel_response, print_html_response, word_response
from .models import (
    AdmissionInfo, Application, ApplicationDraft,
    TuitionStructure, TuitionDiscount, StudentPayment, AdmissionOTP,
)


# ─────────────────────────────────────────────
#  اطلاعات پذیرش
# ─────────────────────────────────────────────
@admin.register(AdmissionInfo)
class AdmissionInfoAdmin(JalaliAdminMixin, admin.ModelAdmin):
    list_display = ['get_degree', 'title', 'deadline_jalali', 'capacity', 'is_open_badge', 'is_active']
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


class HasDocsFilter(admin.SimpleListFilter):
    title = _('مدارک کامل')
    parameter_name = 'docs_complete'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'مدارک کامل'),
            ('no', 'مدارک ناقص'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.exclude(doc_national_id='').exclude(doc_national_id=None).exclude(
                doc_prev_degree=''
            ).exclude(doc_prev_degree=None).exclude(doc_photo='').exclude(doc_photo=None)
        if self.value() == 'no':
            from django.db.models import Q
            return queryset.filter(
                Q(doc_national_id='') | Q(doc_national_id=None)
                | Q(doc_prev_degree='') | Q(doc_prev_degree=None)
                | Q(doc_photo='') | Q(doc_photo=None)
            )
        return queryset


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    change_list_template = 'admin/admissions/application/change_list.html'

    list_display = [
        'tracking_code', 'full_name', 'national_id', 'phone',
        'degree_fa', 'major_name', 'group_name', 'department_name',
        'status_badge', 'phone_verified', 'docs_summary', 'created_jalali',
    ]
    list_filter = [
        'status',
        'degree',
        ('desired_major__group', admin.RelatedOnlyFieldListFilter),
        ('desired_major__department', admin.RelatedOnlyFieldListFilter),
        ('desired_major', admin.RelatedOnlyFieldListFilter),
        'gender',
        'shift',
        'phone_verified',
        HasDocsFilter,
        'created_at',
    ]
    list_editable = []
    search_fields = [
        'tracking_code', 'national_id', 'first_name', 'last_name',
        'phone', 'email', 'father_name',
        'desired_major__name', 'desired_major2__name',
        'desired_major__group__name', 'desired_major__department__name',
    ]
    readonly_fields = [
        'tracking_code', 'created_at_jalali_ro', 'updated_at_jalali_ro',
        'birth_date_jalali_ro', 'interview_date_jalali_ro',
        'doc_national_id_preview', 'doc_prev_degree_preview',
        'doc_photo_preview', 'doc_military_preview',
    ]
    autocomplete_fields = ['desired_major', 'desired_major2']
    inlines = [StudentPaymentInline]
    # date_hierarchy روی MySQL بدون جداول timezone خطای 500 می‌دهد
    list_per_page = 50
    list_select_related = (
        'desired_major',
        'desired_major__group',
        'desired_major__department',
        'desired_major2',
    )
    ordering = ['degree', 'desired_major__group__order', 'desired_major__name', '-created_at']
    save_on_top = True
    actions = [
        'action_mark_reviewing',
        'action_mark_accepted',
        'action_mark_rejected',
        'action_mark_interview',
        'action_mark_incomplete',
        'action_mark_waiting',
        'action_create_student_accounts',
        'action_export_excel',
        'action_export_word',
        'action_export_print',
    ]

    fieldsets = (
        ('کد رهگیری و وضعیت', {
            'fields': (
                ('tracking_code', 'status'),
                ('phone_verified', 'agreed_terms'),
                ('created_at_jalali_ro', 'updated_at_jalali_ro'),
            )
        }),
        ('اطلاعات هویتی', {
            'fields': (
                ('first_name', 'last_name', 'father_name'),
                ('national_id', 'birth_date', 'birth_date_jalali_ro', 'gender'),
                ('birth_cert_no', 'birth_place', 'issue_place'),
                ('marital_status', 'military', 'quota'),
            )
        }),
        ('اطلاعات تماس', {
            'fields': (
                ('phone', 'phone_emergency', 'guardian_name'),
                'email',
                ('province', 'city', 'postal_code'),
                'address',
            )
        }),
        ('سوابق تحصیلی', {
            'fields': (
                ('prev_degree', 'diploma_type', 'prev_major'),
                ('prev_school', 'prev_grad_year'),
                ('gpa', 'diploma_gpa', 'academic_record_code'),
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
                'photo_hijab_confirmed',
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
                ('interview_date', 'interview_date_jalali_ro'),
            ),
            'description': (
                '<strong>یادداشت داخلی</strong> فقط برای کارشناسان است و به متقاضی نمایش داده '
                '<strong>نمی‌شود</strong>. هر پیامی که باید متقاضی ببیند (دلیل رد، مدرک ناقص) '
                'را در «دلیل رد» بنویسید — همان در صفحهٔ پیگیری نمایش داده می‌شود.'
            ),
        }),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                'export/excel/',
                self.admin_site.admin_view(self.export_excel_view),
                name='admissions_application_export_excel',
            ),
            path(
                'export/word/',
                self.admin_site.admin_view(self.export_word_view),
                name='admissions_application_export_word',
            ),
            path(
                'export/print/',
                self.admin_site.admin_view(self.export_print_view),
                name='admissions_application_export_print',
            ),
        ]
        return custom + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        qs = request.GET.urlencode()
        q = f'?{qs}' if qs else ''
        extra_context.update({
            'export_excel_url': reverse('admin:admissions_application_export_excel') + q,
            'export_word_url': reverse('admin:admissions_application_export_word') + q,
            'export_print_url': reverse('admin:admissions_application_export_print') + q,
            'status_counts': self._status_count_cards(request),
        })
        return super().changelist_view(request, extra_context=extra_context)

    def _status_count_cards(self, request):
        base = reverse('admin:admissions_application_changelist')
        rows = (
            Application.objects.values('status')
            .annotate(n=Count('id'))
            .order_by()
        )
        counts = {r['status']: r['n'] for r in rows}
        cards = []
        total = sum(counts.values())
        cards.append(('__all__', 'همه', total, base))
        for key, label in Application.STATUS_CHOICES:
            cards.append((key, label, counts.get(key, 0), f'{base}?status__exact={key}'))
        return cards

    def _export_queryset(self, request):
        """اعمال همان فیلتر/جستجوی صفحه‌لیست روی خروجی."""
        try:
            cl = self.get_changelist_instance(request)
            qs = cl.get_queryset(request)
        except Exception:
            qs = self.get_queryset(request)
        return qs.select_related(
            'desired_major',
            'desired_major__group',
            'desired_major__department',
            'desired_major2',
        ).order_by('degree', 'desired_major__group__name', 'desired_major__name', 'last_name')

    # این سه ویو کد ملی، موبایل، ایمیل و معدل متقاضیان را برمی‌گردانند؛
    # admin_view فقط is_staff را چک می‌کند، پس گارد مجوز مدل الزامی است.
    @require_model_view_permission
    def export_excel_view(self, request):
        qs = self._export_queryset(request)
        return excel_response(qs, 'applications.xlsx', title='لیست درخواست‌های پذیرش')

    @require_model_view_permission
    def export_word_view(self, request):
        qs = self._export_queryset(request)
        return word_response(qs, 'applications.docx', title='لیست درخواست‌های پذیرش')

    @require_model_view_permission
    def export_print_view(self, request):
        qs = self._export_queryset(request)
        title = 'لیست درخواست‌های پذیرش'
        if request.GET.get('status__exact') == 'accepted':
            title = 'لیست پذیرفته‌شدگان'
        return print_html_response(qs, title=title)

    # ── ستون‌های لیست ──
    @admin.display(description='نام متقاضی', ordering='last_name')
    def full_name(self, obj):
        return f'{obj.first_name} {obj.last_name}'

    @admin.display(description='مقطع', ordering='degree')
    def degree_fa(self, obj):
        return obj.get_degree_display()

    @admin.display(description='رشته', ordering='desired_major__name')
    def major_name(self, obj):
        return obj.desired_major.name if obj.desired_major_id else '—'

    @admin.display(description='گروه آموزشی', ordering='desired_major__group__name')
    def group_name(self, obj):
        major = obj.desired_major
        if major and major.group_id:
            return major.group.name
        return '—'

    @admin.display(description='دانشکده', ordering='desired_major__department__name')
    def department_name(self, obj):
        major = obj.desired_major
        if major and major.department_id:
            return major.department.name
        return '—'

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

    @admin.display(description='تاریخ ثبت', ordering='created_at')
    def created_jalali(self, obj):
        from core.jalali import format_jalali_datetime, jalali_year_range
        return format_jalali_datetime(obj.created_at)

    @admin.display(description='تاریخ ثبت (شمسی)')
    def created_at_jalali_ro(self, obj):
        from core.jalali import format_jalali_datetime
        return format_jalali_datetime(obj.created_at) if obj and obj.created_at else '—'

    @admin.display(description='آخرین به‌روزرسانی (شمسی)')
    def updated_at_jalali_ro(self, obj):
        from core.jalali import format_jalali_datetime
        return format_jalali_datetime(obj.updated_at) if obj and obj.updated_at else '—'

    @admin.display(description='تاریخ تولد (شمسی)')
    def birth_date_jalali_ro(self, obj):
        from core.jalali import format_jalali_date
        return format_jalali_date(obj.birth_date, 'full') if obj and obj.birth_date else '—'

    @admin.display(description='مصاحبه (شمسی)')
    def interview_date_jalali_ro(self, obj):
        from core.jalali import format_jalali_datetime
        return format_jalali_datetime(obj.interview_date) if obj and obj.interview_date else '—'

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
        # Django 5+: format_html بدون آرگومان TypeError می‌دهد
        return mark_safe(''.join(parts))

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

    # ── اکشن‌های گروهی ──
    def _bulk_status(self, request, queryset, status, label):
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

    @admin.action(description='ساخت حساب دانشجویی برای پذیرفته‌شدگان انتخاب‌شده')
    def action_create_student_accounts(self, request, queryset):
        """
        متقاضی پذیرفته‌شده → حساب کاربری + پروفایل دانشجو.

        ۱۵ فیلد مشترک بین Application و UserProfile توسط
        `dashboard.onboarding.sync_profile_from_application` کپی می‌شود، پس
        اطلاعات هویتی دوباره دستی وارد نمی‌شود. نام کاربری = کد ملی.
        رمز عبور تصادفی ساخته می‌شود؛ دانشجو با «فراموشی رمز» یا لینک ورود
        پیامکی وارد می‌شود — رمز هیچ‌جا نمایش یا ذخیره نمی‌شود.
        """
        from django.contrib.auth.models import User
        from django.db import transaction
        from django.utils.crypto import get_random_string

        from accounts.models import UserProfile
        from dashboard.onboarding import sync_profile_from_application

        created, linked, skipped = 0, 0, []

        for app in queryset.select_related('desired_major'):
            if app.status != 'accepted':
                skipped.append(f'{app.tracking_code} (پذیرفته نشده)')
                continue
            nid = (app.national_id or '').strip()
            if not nid:
                skipped.append(f'{app.tracking_code} (بدون کد ملی)')
                continue

            try:
                with transaction.atomic():
                    user = User.objects.filter(username=nid).first()
                    if user is None:
                        user = User.objects.create_user(
                            username=nid,
                            email=(app.email or '').strip(),
                            # make_random_password در جنگو ۵ حذف شده است
                            password=get_random_string(20),
                            first_name=app.first_name or '',
                            last_name=app.last_name or '',
                        )
                        created += 1
                    else:
                        linked += 1

                    profile, _ = UserProfile.objects.get_or_create(user=user)
                    if profile.role == 'student' or not profile.role:
                        profile.role = 'student'
                        profile.save(update_fields=['role'])
                    # ۱۵ فیلد مشترک را از پرونده پذیرش پر می‌کند
                    sync_profile_from_application(user, app)
            except Exception as exc:  # noqa: BLE001
                skipped.append(f'{app.tracking_code} ({exc})')

        if created or linked:
            self.message_user(
                request,
                f'{created} حساب جدید ساخته شد، {linked} متقاضی به حساب موجود وصل شد. '
                'اطلاعات هویتی از پرونده پذیرش کپی شد.',
                messages.SUCCESS,
            )
        if skipped:
            preview = '، '.join(skipped[:5])
            more = f' و {len(skipped) - 5} مورد دیگر' if len(skipped) > 5 else ''
            self.message_user(
                request, f'{len(skipped)} مورد رد شد: {preview}{more}', messages.WARNING,
            )

    @admin.action(description='خروجی اکسل از انتخاب‌شده‌ها')
    def action_export_excel(self, request, queryset):
        qs = queryset.select_related(
            'desired_major', 'desired_major__group', 'desired_major__department', 'desired_major2',
        )
        return excel_response(qs, 'applications-selected.xlsx', title='لیست انتخاب‌شده پذیرش')

    @admin.action(description='خروجی ورد از انتخاب‌شده‌ها')
    def action_export_word(self, request, queryset):
        qs = queryset.select_related(
            'desired_major', 'desired_major__group', 'desired_major__department', 'desired_major2',
        )
        return word_response(qs, 'applications-selected.docx', title='لیست انتخاب‌شده پذیرش')

    @admin.action(description='چاپ / PDF از انتخاب‌شده‌ها')
    def action_export_print(self, request, queryset):
        qs = queryset.select_related(
            'desired_major', 'desired_major__group', 'desired_major__department', 'desired_major2',
        )
        return print_html_response(qs, title='لیست انتخاب‌شده پذیرش')


@admin.register(TuitionStructure)
class TuitionStructureAdmin(admin.ModelAdmin):
    list_display = [
        'major', 'degree_display', 'academic_year_jalali', 'fixed_fee_fmt',
        'theory_fee_fmt', 'practical_fee_fmt', 'is_active',
    ]
    list_filter = ['major__degree', 'academic_year', 'is_active', 'major__group']
    list_editable = ['is_active']
    search_fields = ['major__name', 'academic_year']
    autocomplete_fields = ['major']
    list_select_related = ('major', 'major__group')

    @admin.display(description='سال تحصیلی', ordering='academic_year')
    def academic_year_jalali(self, obj):
        """سال را شمسی نشان می‌دهد حتی اگر میلادی ذخیره شده باشد.

        `fix_academic_years` خودِ داده را اصلاح می‌کند، ولی کسی ممکن
        است بعداً «2027-2028» تایپ کند و آن‌وقت فهرست نباید میلادی
        نشان بدهد.
        """
        return jalali_year_range(obj.academic_year)
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
class StudentPaymentAdmin(JalaliAdminMixin, admin.ModelAdmin):
    list_display = [
        'application', 'installment_no', 'amount_fmt',
        'due_date_jalali', 'status_badge', 'confirmed_by',
    ]
    list_filter = ['status', 'due_date']
    search_fields = [
        'application__tracking_code', 'application__first_name',
        'application__last_name', 'application__national_id',
    ]
    readonly_fields = ['paid_at']
    autocomplete_fields = ['application']
    list_select_related = ('application',)
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
class AdmissionOTPAdmin(JalaliAdminMixin, admin.ModelAdmin):
    list_display = ['phone', 'created_jalali', 'expires_jalali', 'is_used', 'attempts']
    list_filter = ['is_used', 'created_at']
    search_fields = ['phone']
    readonly_fields = ['phone', 'created_at', 'expires_at', 'attempts', 'is_used']
    fieldsets = (
        ('کد تأیید موبایل', {
            'fields': ('phone', 'is_used', 'attempts', 'created_at', 'expires_at'),
            'description': (
                'خودِ کد نمایش داده نمی‌شود؛ نمایش آن یعنی دارندهٔ دسترسی می‌تواند '
                'کد فعال یک شماره را بخواند و مرحلهٔ تأیید موبایل را جای او بگذراند. '
                'شمارهٔ تلاش، زمان انقضا و وضعیت مصرف برای پیگیری امنیتی کافی است.'
            ),
        }),
    )


@admin.register(ApplicationDraft)
class ApplicationDraftAdmin(admin.ModelAdmin):
    """پیش‌نویس‌های نیمه‌کاره — برای دیدن اینکه کجا رها می‌شوند.

    فقط خواندنی است: این‌ها دادهٔ متقاضی‌اند و ویرایششان از اینجا
    معنایی ندارد. حذف باز است تا بشود پیش‌نویس‌های کهنه را پاک کرد.
    """
    list_display = ('phone', 'filled_ratio', 'updated_at')
    search_fields = ('phone',)
    readonly_fields = ('phone', 'payload', 'updated_at')

    def has_add_permission(self, request):
        return False
