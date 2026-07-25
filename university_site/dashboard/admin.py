from django.contrib import admin, messages
from django.db.models import Count, Q
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html

from .models import (
    Semester, Enrollment, TeachingAssignment, StudentRequest,
    Payment, ExamSchedule, Assignment, AssignmentSubmission, Attendance,
    TuitionInstallmentPlan, StudentDiscountClaim,
)
from .onboarding import reapply_discount_to_pending


@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display = ['name', 'semester_type', 'academic_year', 'start_date', 'end_date', 'is_active', 'registration_open']
    list_filter = ['semester_type', 'is_active', 'registration_open']
    search_fields = ['name', 'academic_year']


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    change_list_template = 'admin/dashboard/enrollment_changelist.html'

    list_display = [
        'student', 'major_name', 'course', 'semester',
        'status_badge', 'mid_term_grade', 'final_grade', 'enrolled_at',
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


@admin.register(TeachingAssignment)
class TeachingAssignmentAdmin(admin.ModelAdmin):
    list_display = [
        'professor', 'course', 'major_name', 'semester',
        'department', 'classroom', 'enrollment_count', 'is_active',
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
class StudentRequestAdmin(admin.ModelAdmin):
    list_display = ['student', 'request_type', 'title', 'status', 'created_at']
    list_filter = ['request_type', 'status', 'created_at']
    search_fields = ['student__first_name', 'student__last_name', 'title']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'student', 'payment_type', 'installment_no', 'installment_stage',
        'amount', 'method', 'due_date', 'semester', 'status', 'gateway',
        'receipt_ref', 'payment_date',
    ]
    list_filter = ['status', 'method', 'payment_type', 'installment_stage', 'gateway', 'semester']
    search_fields = [
        'student__first_name', 'student__last_name', 'student__username',
        'transaction_id', 'authority', 'receipt_ref', 'exam_barcode',
    ]
    readonly_fields = ['authority', 'transaction_id', 'payment_date', 'created_at', 'reminder_sent_at', 'exam_barcode']
    actions = ['confirm_offline_payments', 'reject_offline_payments']

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
class TuitionInstallmentPlanAdmin(admin.ModelAdmin):
    list_display = [
        'academic_year', 'ratio_initial', 'ratio_mid', 'ratio_exam',
        'due_days_initial', 'due_days_mid', 'due_days_exam',
        'reminder_days_before', 'is_active',
    ]
    list_filter = ['is_active']
    search_fields = ['academic_year']


@admin.register(StudentDiscountClaim)
class StudentDiscountClaimAdmin(admin.ModelAdmin):
    list_display = [
        'student', 'semester', 'discount_type', 'percent', 'status',
        'created_at', 'reviewed_at',
    ]
    list_filter = ['status', 'discount_type', 'semester']
    search_fields = ['student__first_name', 'student__last_name', 'student__username']
    actions = ['approve_claims', 'reject_claims']

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
class ExamScheduleAdmin(admin.ModelAdmin):
    list_display = ['course', 'semester', 'exam_type', 'date', 'start_time', 'end_time', 'location']
    list_filter = ['exam_type', 'semester', 'date']
    search_fields = ['course__name', 'location']


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['course', 'semester', 'professor', 'title', 'assignment_type', 'due_date', 'max_score', 'is_active']
    list_filter = ['assignment_type', 'semester', 'is_active']
    search_fields = ['course__name', 'professor__first_name', 'professor__last_name', 'title']


@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):
    list_display = ['assignment', 'student', 'submitted_at', 'grade', 'status']
    list_filter = ['status', 'assignment__semester']
    search_fields = ['student__first_name', 'student__last_name', 'assignment__title']


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['enrollment', 'date', 'status']
    list_filter = ['status', 'date']
    search_fields = ['enrollment__student__first_name', 'enrollment__student__last_name']
