from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),

    # دانشجو
    path('courses/', views.student_courses, name='student_courses'),
    path('registration/', views.student_registration, name='student_registration'),
    path('schedule/', views.student_schedule, name='student_schedule'),
    path('schedule/print/', views.print_class_schedule, name='print_class_schedule'),
    path('schedule/calendar.ics', views.student_calendar_ics, name='student_calendar_ics'),
    path('exam-card/', views.student_exam_card, name='student_exam_card'),
    path('grades/', views.student_grades, name='student_grades'),
    path('grades/transcript/', views.print_transcript, name='print_transcript'),
    path('requests/', views.student_requests, name='student_requests'),
    path('assignments/', views.student_assignments, name='student_assignments'),
    path('assignments/<int:pk>/submit/', views.student_assignment_submit, name='student_assignment_submit'),
    path('exams/', views.student_exams, name='student_exams'),
    path('payments/', views.student_payments, name='student_payments'),
    path('payments/print/', views.print_tuition_receipt, name='print_tuition_receipt'),
    path('payments/<int:pk>/print/', views.print_tuition_receipt, name='print_tuition_receipt_one'),
    path('payments/<int:pk>/pay/', views.payment_start, name='payment_start'),
    path('payments/<int:pk>/offline/', views.payment_offline, name='payment_offline'),
    path('payments/<int:pk>/mock/', views.payment_mock, name='payment_mock'),
    path('payments/callback/', views.payment_callback, name='payment_callback'),
    path('payments/discount/', views.tuition_discount_claim, name='tuition_discount_claim'),
    path('clearance/', views.student_clearance, name='student_clearance'),
    path('lifecycle/', views.student_lifecycle, name='student_lifecycle'),

    # استاد
    path('teaching/', views.professor_courses, name='professor_courses'),
    path('teaching/<int:pk>/', views.professor_course_detail, name='professor_course_detail'),
    path('teaching/<int:pk>/print/', views.professor_print_roster, name='professor_print_roster'),
    path('teaching/<int:pk>/attendance/', views.professor_attendance, name='professor_attendance'),
    path('teaching/grade/<int:enrollment_id>/', views.professor_grade_edit, name='professor_grade_edit'),
    path('teaching/assignments/', views.professor_assignments, name='professor_assignments'),
    path('teaching/assignments/<int:pk>/submissions/', views.professor_submissions, name='professor_submissions'),
    path('teaching/submissions/<int:pk>/grade/', views.professor_grade_submission, name='professor_grade_submission'),

    # کارکنان
    path('staff/requests/', views.staff_requests, name='staff_requests'),
    path('staff/requests/<int:pk>/', views.staff_request_respond, name='staff_request_respond'),
    path('staff/students/export/', views.staff_student_export, name='staff_student_export'),
]
