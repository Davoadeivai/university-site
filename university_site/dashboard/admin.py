from django.contrib import admin, messages
from django.db.models import Count, Q
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html

from core.admin_guards import require_model_view_permission
from core.admin_jalali import JalaliAdminMixin
from core.jalali import format_jalali_date, format_jalali_datetime

from .models import (
    Semester, Enrollment, TeachingAssignment, StudentRequest,
    Payment, ExamSchedule, Assignment, AssignmentSubmission, Attendance,
    TuitionInstallmentPlan, StudentDiscountClaim,
    StudentClearance, StudentClearanceItem, StudentLifecycleRequest,
    ClassSession,
)
from .onboarding import reapply_discount_to_pending


@admin.register(Semester)
class SemesterAdmin(JalaliAdminMixin, admin.ModelAdmin):
    list_display = [
        'name_jalali', 'semester_type', 'academic_year_jalali',
        'start_date_jalali', 'end_date_jalali',
        'is_active', 'registration_open',
    ]
    list_filter = ['semester_type', 'is_active', 'registration_open']
    search_fields = ['name', 'academic_year']
    readonly_fields = ['start_date_jalali_ro', 'end_date_jalali_ro']

    fieldsets = (
        (None, {
            'fields': (
                'name', 'semester_type', 'academic_year',
                'start_date', 'start_date_jalali_ro',
                'end_date', 'end_date_jalali_ro',
                'is_active', 'registration_open',
            ),
        }),
    )

    @admin.display(description='شروع (شمسی)')
    def start_date_jalali_ro(self, obj):
        return format_jalali_date(obj.start_date, 'full') if obj and obj.start_date else '—'

    @admin.display(description='پایان (شمسی)')
    def end_date_jalali_ro(self, obj):
        return format_jalali_date(obj.end_date, 'full') if obj and obj.end_date else '—'


@admin.register(Enrollment)
class EnrollmentAdmin(JalaliAdminMixin, admin.ModelAdmin):
    change_list_template = 'admin/dashboard/enrollment_changelist.html'

    list_display = [
        'student', 'major_name', 'course', 'semester',
        'status_badge', 'mid_term_grade', 'final_grade', 'enrolled_jalali',
    ]
    list_filter = [
        'status',
        'semester',
        ('course__major__group', admin.RelatedOnlyFieldListFilter),
        ('course__major', admin.RelatedOnlyFieldListFilter),
    ]
    search_fields = [
        'student__first_name', 'student__last_name', 'student__username',
        'course__name', 'course__major__name',
    ]
    list_select_related = (
        'student', 'course', 'course__major', 'course__major__group', 'semester',
    )
    ordering = ['semester', 'course__major__group__order', 'course__major__name', 'student__last_name']

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                'enrollment-report/',
                self.admin_site.admin_view(self.enrollment_report_view),
                name='dashboard_enrollment_report',
            ),
        ]
        return custom + urls

    @require_model_view_permission
    def enrollment_report_view(self, request):
        """داشبورد آماری انتخاب‌واحد به تفکیک رشته و ترم"""
        from academics.models import Major

        all_semesters = Semester.objects.order_by('-academic_year', '-start_date')
        selected_sid = request.GET.get('semester', '')
        if selected_sid:
            try:
                semester = Semester.objects.get(pk=selected_sid)
            except Semester.DoesNotExist:
                semester = Semester.objects.filter(is_active=True).first()
        else:
            semester = Semester.objects.filter(is_active=True).first()

        rows = []
        total_enrollments = 0
        total_students = 0
        total_majors = 0
        dropped_count = 0

        if semester:
            active_qs = Enrollment.objects.filter(semester=semester)
            total_enrollments = active_qs.exclude(status='dropped').count()
            total_students = active_qs.exclude(status='dropped').values('student').distinct().count()
            dropped_count = active_qs.filter(status='dropped').count()

            majors_with_data = (
                Major.objects.filter(
                    courses__enrollments__semester=semester,
                ).distinct().select_related('group', 'department')
            )
            total_majors = majors_with_data.count()

            for major in majors_with_data.order_by('group__order', 'name'):
                enroll_qs = active_qs.filter(course__major=major)
                enroll_count = enroll_qs.exclude(status='dropped').count()
                student_count = enroll_qs.exclude(status='dropped').values('student').distinct().count()
                d_count = enroll_qs.filter(status='dropped').count()
                rows.append({
                    'major_id': major.pk,
                    'major_name': major.name,
                    'degree_display': major.get_degree_display(),
                    'group_name': major.group.name if major.group_id else '',
                    'student_count': student_count,
                    'enroll_count': enroll_count,
                    'dropped_count': d_count,
                    'capacity': major.capacity,
                })

        ctx = {
            **self.admin_site.each_context(request),
            'title': 'گزارش انتخاب‌واحد',
            'active_semester': semester,
            'all_semesters': all_semesters,
            'selected_semester_id': selected_sid,
            'rows': rows,
            'summary': {
                'total_enrollments': total_enrollments,
                'total_students': total_students,
                'total_majors': total_majors,
                'dropped_count': dropped_count,
            },
        }
        return render(request, 'admin/dashboard/enrollment_report.html', ctx)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['report_url'] = reverse('admin:dashboard_enrollment_report')
        return super().changelist_view(request, extra_context=extra_context)

    @admin.display(description='رشته', ordering='course__major__name')
    def major_name(self, obj):
        major = obj.course.major
        return format_html(
            '<span style="white-space:nowrap;">{}</span>',
            f'{major.name} ({major.get_degree_display()})',
        )

    @admin.display(description='وضعیت', ordering='status')
    def status_badge(self, obj):
        colors = {
            'registered':   '#3b82f6',
            'in_progress':  '#06b6d4',
            'completed':    '#16a34a',
            'dropped':      '#dc2626',
            'failed':       '#f59e0b',
        }
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:10px;font-size:12px;white-space:nowrap;">{}</span>',
            colors.get(obj.status, '#64748b'),
            obj.get_status_display(),
        )


class ClassSessionInline(admin.TabularInline):
    model = ClassSession
    extra = 1
    verbose_name = 'جلسه هفتگی'
    verbose_name_plural = 'جلسات هفتگی (مبنای تشخیص تداخل ساعت)'


@admin.register(ClassSession)
class ClassSessionAdmin(admin.ModelAdmin):
    list_display = ['teaching_assignment', 'day', 'start_time', 'end_time']
    list_filter = ['day', 'teaching_assignment__semester']
    search_fields = [
        'teaching_assignment__course__name',
        'teaching_assignment__professor__last_name',
    ]
    list_select_related = ('teaching_assignment', 'teaching_assignment__course')


@admin.register(TeachingAssignment)
class TeachingAssignmentAdmin(admin.ModelAdmin):
    inlines = [ClassSessionInline]
    list_display = [
        'professor', 'course', 'major_name', 'semester',
        'department', 'classroom', 'seats_display', 'enrollment_count', 'is_active',
    ]
    list_filter = [
        'semester',
        'department',
        'is_active',
        ('course__major__group', admin.RelatedOnlyFieldListFilter),
        ('course__major', admin.RelatedOnlyFieldListFilter),
    ]
    search_fields = [
        'professor__first_name', 'professor__last_name',
        'course__name', 'course__major__name',
    ]
    list_select_related = ('professor', 'course', 'course__major', 'semester', 'department')

    @admin.display(description='ظرفیت / باقیمانده')
    def seats_display(self, obj):
        if not obj.capacity:
            return 'نامحدود'
        left = obj.remaining_seats
        color = '#dc2626' if left == 0 else ('#f59e0b' if left <= 3 else '#16a34a')
        return format_html(
            '<span style="color:{};font-weight:700;">{} / {}</span>',
            color, left, obj.capacity,
        )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_enroll_count=Count('enrollments'))

    @admin.display(description='رشته', ordering='course__major__name')
    def major_name(self, obj):
        return obj.course.major.name

    @admin.display(description='ثبت‌نام‌شده', ordering='_enroll_count')
    def enrollment_count(self, obj):
        n = obj._enroll_count
        color = '#16a34a' if n > 0 else '#94a3b8'
        return format_html('<span style="color:{};font-weight:600;">{}</span>', color, n)


@admin.register(StudentRequest)
class StudentRequestAdmin(JalaliAdminMixin, admin.ModelAdmin):
    list_display = ['student', 'request_type', 'title', 'status', 'created_jalali']
    list_filter = ['request_type', 'status', 'created_at']
    search_fields = ['student__first_name', 'student__last_name', 'title']
    list_select_related = ('student',)


@admin.register(Payment)
class PaymentAdmin(JalaliAdminMixin, admin.ModelAdmin):
    list_display = [
        'student', 'payment_type', 'installment_no', 'installment_stage',
        'amount', 'method', 'due_date_jalali', 'semester', 'status', 'gateway',
        'receipt_ref', 'payment_date_jalali',
    ]
    list_filter = ['status', 'method', 'payment_type', 'installment_stage', 'gateway', 'semester']
    search_fields = [
        'student__first_name', 'student__last_name', 'student__username',
        'transaction_id', 'authority', 'receipt_ref', 'exam_barcode',
    ]
    readonly_fields = [
        'authority', 'transaction_id', 'payment_date_jalali_ro',
        'created_jalali', 'reminder_sent_at', 'exam_barcode',
    ]
    list_select_related = ('student', 'semester')
    actions = ['confirm_offline_payments', 'reject_offline_payments']

    @admin.display(description='تاریخ پرداخت (شمسی)')
    def payment_date_jalali_ro(self, obj):
        return format_jalali_datetime(obj.payment_date) if obj and obj.payment_date else '—'

    @admin.action(description='تأیید پرداخت آفلاین (کارت‌به‌کارت / کارتخوان / فیش / نقدی)')
    def confirm_offline_payments(self, request, queryset):
        qs = queryset.filter(status='review')
        n = 0
        for p in qs:
            p.status = 'paid'
            p.payment_date = timezone.now()
            if not p.transaction_id and p.receipt_ref:
                p.transaction_id = p.receipt_ref
            p.save(update_fields=['status', 'payment_date', 'transaction_id'])
            n += 1
        self.message_user(request, f'{n} پرداخت آفلاین تأیید شد.', messages.SUCCESS)

    @admin.action(description='رد پرداخت آفلاین — برگشت به در انتظار')
    def reject_offline_payments(self, request, queryset):
        n = queryset.filter(status='review').update(status='pending')
        self.message_user(request, f'{n} مورد رد و به «در انتظار» برگشت.', messages.WARNING)


@admin.register(TuitionInstallmentPlan)
class TuitionInstallmentPlanAdmin(JalaliAdminMixin, admin.ModelAdmin):
    list_display = [
        'academic_year_jalali', 'ratio_initial', 'ratio_mid', 'ratio_exam',
        'due_days_initial', 'due_days_mid', 'due_days_exam',
        'reminder_days_before', 'is_active',
    ]
    list_filter = ['is_active']
    search_fields = ['academic_year']


@admin.register(StudentDiscountClaim)
class StudentDiscountClaimAdmin(JalaliAdminMixin, admin.ModelAdmin):
    list_display = [
        'student', 'semester', 'discount_type', 'percent', 'status',
        'created_jalali', 'reviewed_jalali',
    ]
    list_filter = ['status', 'discount_type', 'semester']
    search_fields = ['student__first_name', 'student__last_name', 'student__username']
    list_select_related = ('student', 'semester')
    actions = ['approve_claims', 'reject_claims']

    @admin.display(description='بررسی', ordering='reviewed_at')
    def reviewed_jalali(self, obj):
        return format_jalali_datetime(obj.reviewed_at) if obj.reviewed_at else '—'

    @admin.action(description='تأیید تخفیف و بازتوزیع اقساط پرداخت‌نشده')
    def approve_claims(self, request, queryset):
        n = 0
        for claim in queryset.exclude(status='approved'):
            claim.status = 'approved'
            claim.reviewed_at = timezone.now()
            claim.save(update_fields=['status', 'reviewed_at'])
            reapply_discount_to_pending(claim.student, claim.semester)
            n += 1
        self.message_user(request, f'{n} تخفیف تأیید شد.', messages.SUCCESS)

    @admin.action(description='رد درخواست تخفیف')
    def reject_claims(self, request, queryset):
        n = queryset.exclude(status='rejected').update(
            status='rejected', reviewed_at=timezone.now()
        )
        self.message_user(request, f'{n} درخواست رد شد.', messages.WARNING)


@admin.register(ExamSchedule)
class ExamScheduleAdmin(JalaliAdminMixin, admin.ModelAdmin):
    list_display = ['course', 'semester', 'exam_type', 'date_jalali', 'start_time', 'end_time', 'location']
    list_filter = ['exam_type', 'semester', 'date']
    search_fields = ['course__name', 'location']
    list_select_related = ('course', 'semester')


@admin.register(Assignment)
class AssignmentAdmin(JalaliAdminMixin, admin.ModelAdmin):
    list_display = [
        'course', 'semester', 'professor', 'title', 'assignment_type',
        'due_date_jalali', 'max_score', 'is_active',
    ]
    list_filter = ['assignment_type', 'semester', 'is_active']
    search_fields = ['course__name', 'professor__first_name', 'professor__last_name', 'title']
    list_select_related = ('course', 'semester', 'professor')


@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(JalaliAdminMixin, admin.ModelAdmin):
    list_display = ['assignment', 'student', 'submitted_jalali', 'grade', 'status']
    list_filter = ['status', 'assignment__semester']
    search_fields = ['student__first_name', 'student__last_name', 'assignment__title']
    list_select_related = ('assignment', 'student')

    @admin.display(description='ارسال', ordering='submitted_at')
    def submitted_jalali(self, obj):
        return format_jalali_datetime(obj.submitted_at) if obj.submitted_at else '—'


@admin.register(Attendance)
class AttendanceAdmin(JalaliAdminMixin, admin.ModelAdmin):
    list_display = ['enrollment', 'date_jalali', 'status']
    list_filter = ['status', 'date']
    search_fields = ['enrollment__student__first_name', 'enrollment__student__last_name']
    list_select_related = ('enrollment', 'enrollment__student')


class StudentClearanceItemInline(admin.TabularInline):
    model = StudentClearanceItem
    extra = 0
    fields = ['department', 'status', 'cleared_at', 'note']


@admin.register(StudentClearance)
class StudentClearanceAdmin(JalaliAdminMixin, admin.ModelAdmin):
    list_display = ['student', 'status', 'completed_jalali', 'updated_jalali']
    list_filter = ['status']
    search_fields = [
        'student__username', 'student__first_name', 'student__last_name',
        'student__profile__national_id',
    ]
    autocomplete_fields = ['student']
    list_select_related = ('student',)
    inlines = [StudentClearanceItemInline]
    readonly_fields = ['created_at', 'updated_at', 'completed_at']

    @admin.display(description='تکمیل', ordering='completed_at')
    def completed_jalali(self, obj):
        return format_jalali_datetime(obj.completed_at) if obj.completed_at else '—'

    @admin.display(description='بروزرسانی', ordering='updated_at')
    def updated_jalali(self, obj):
        return format_jalali_datetime(obj.updated_at) if obj.updated_at else '—'

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        form.instance.ensure_items()
        form.instance.refresh_status()


@admin.register(StudentLifecycleRequest)
class StudentLifecycleRequestAdmin(JalaliAdminMixin, admin.ModelAdmin):
    list_display = [
        'student', 'request_type', 'status_badge', 'created_jalali', 'reviewed_jalali',
    ]
    list_filter = ['request_type', 'status']
    search_fields = [
        'student__username', 'student__first_name', 'student__last_name',
        'student__profile__national_id', 'reason',
    ]
    autocomplete_fields = ['student', 'reviewed_by']
    list_select_related = ('student', 'reviewed_by')
    readonly_fields = ['created_at', 'updated_at', 'reviewed_at']
    actions = ['approve_requests', 'reject_requests', 'mark_under_review']

    fieldsets = (
        (None, {
            'fields': (
                'student', 'request_type', 'status', 'reason', 'attachment',
            ),
        }),
        ('پاسخ ادمین', {
            'fields': ('admin_response', 'reviewed_by', 'reviewed_at'),
        }),
        ('زمان', {
            'fields': ('created_at', 'updated_at'),
        }),
    )

    @admin.display(description='وضعیت')
    def status_badge(self, obj):
        colors = {
            'draft': '#6c757d',
            'submitted': '#0d6efd',
            'under_review': '#fd7e14',
            'approved': '#198754',
            'rejected': '#dc3545',
            'cancelled': '#6c757d',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:6px;font-size:12px;">{}</span>',
            color, obj.get_status_display(),
        )

    @admin.display(description='ثبت', ordering='created_at')
    def created_jalali(self, obj):
        return format_jalali_datetime(obj.created_at) if obj.created_at else '—'

    @admin.display(description='بررسی', ordering='reviewed_at')
    def reviewed_jalali(self, obj):
        return format_jalali_datetime(obj.reviewed_at) if obj.reviewed_at else '—'

    @admin.action(description='تأیید و اعمال وضعیت تحصیلی')
    def approve_requests(self, request, queryset):
        n = 0
        for req in queryset.exclude(status='approved'):
            if req.needs_clearance:
                clearance = getattr(req.student, 'clearance', None)
                if clearance is None or not clearance.is_complete:
                    self.message_user(
                        request,
                        f'تسویه {req.student} تکمیل نشده؛ درخواست {req.pk} رد نشد اما تأیید نشد.',
                        messages.WARNING,
                    )
                    continue
            req.apply_approval(reviewer=request.user)
            n += 1
        self.message_user(request, f'{n} درخواست تأیید شد.', messages.SUCCESS)

    @admin.action(description='رد درخواست')
    def reject_requests(self, request, queryset):
        n = queryset.exclude(status__in=('approved', 'rejected')).update(
            status='rejected',
            reviewed_at=timezone.now(),
            reviewed_by=request.user,
        )
        self.message_user(request, f'{n} درخواست رد شد.', messages.WARNING)

    @admin.action(description='علامت‌گذاری «در حال بررسی»')
    def mark_under_review(self, request, queryset):
        n = queryset.filter(status__in=('draft', 'submitted')).update(status='under_review')
        self.message_user(request, f'{n} درخواست به بررسی منتقل شد.', messages.INFO)