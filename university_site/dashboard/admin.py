from django.contrib import admin
from .models import (
    Semester, Enrollment, TeachingAssignment, StudentRequest,
    Payment, ExamSchedule, Assignment, AssignmentSubmission, Attendance
)


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
    list_display = ['student', 'payment_type', 'amount', 'semester', 'status', 'gateway', 'transaction_id', 'payment_date']
    list_filter = ['status', 'payment_type', 'gateway', 'semester']
    search_fields = ['student__first_name', 'student__last_name', 'student__username', 'transaction_id', 'authority']
    readonly_fields = ['authority', 'transaction_id', 'payment_date', 'created_at']


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
