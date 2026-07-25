from django.contrib import admin, messages
from django.utils import timezone

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
    list_display = ['student', 'course', 'semester', 'status', 'mid_term_grade', 'final_grade', 'enrolled_at']
    list_filter = ['status', 'semester']
    search_fields = ['student__first_name', 'student__last_name', 'course__name']


@admin.register(TeachingAssignment)
class TeachingAssignmentAdmin(admin.ModelAdmin):
    list_display = ['professor', 'course', 'semester', 'department', 'classroom', 'is_active']
    list_filter = ['semester', 'department', 'is_active']
    search_fields = ['professor__first_name', 'professor__last_name', 'course__name']


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
