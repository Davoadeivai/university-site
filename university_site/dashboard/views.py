from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils import timezone
from news.models import News
from admissions.models import Application
from contact.models import ContactMessage
from accounts.models import Announcement
from .models import (
    Enrollment, TeachingAssignment, StudentRequest,
    Payment, ExamSchedule, Assignment, Semester,
)


@login_required
def dashboard(request):
    user = request.user
    try:
        role = user.profile.role
    except Exception:
        role = 'student'

    context = {'role': role, 'page_title': 'داشبورد'}

    # ──────────────────────────────────────────────
    # ادمین — دسترسی کامل
    # ──────────────────────────────────────────────
    if role == 'admin' or user.is_staff:
        context.update({
            'page_title': 'داشبورد ادمین',
            'total_news': News.objects.filter(is_published=True).count(),
            'total_applications': Application.objects.count(),
            'new_messages': ContactMessage.objects.filter(status='new').count(),
            'total_users': User.objects.count(),
            'pending_requests': StudentRequest.objects.filter(status='pending').count(),
            'recent_news': News.objects.filter(is_published=True).order_by('-published_at')[:5],
            'recent_applications': Application.objects.order_by('-created_at')[:5],
            'recent_messages': ContactMessage.objects.filter(status='new').order_by('-created_at')[:5],
            'recent_requests': StudentRequest.objects.order_by('-created_at')[:5],
        })

    # ──────────────────────────────────────────────
    # مدیر دانشگاه (staff) — آمار کلی دانشگاه
    # ──────────────────────────────────────────────
    elif role == 'staff':
        context.update({
            'page_title': 'داشبورد مدیریت دانشگاه',
            'total_students': User.objects.filter(profile__role='student').count(),
            'total_professors': User.objects.filter(profile__role='professor').count(),
            'total_applications': Application.objects.count(),
            'pending_applications': Application.objects.filter(status='pending').count(),
            'new_messages': ContactMessage.objects.filter(status='new').count(),
            'total_news': News.objects.filter(is_published=True).count(),
            'pending_requests': StudentRequest.objects.filter(status='pending').count(),
            'recent_applications': Application.objects.order_by('-created_at')[:5],
            'recent_messages': ContactMessage.objects.filter(status='new').order_by('-created_at')[:5],
            'recent_requests': StudentRequest.objects.order_by('-created_at')[:5],
            'announcements': Announcement.objects.filter(
                is_active=True, target__in=['all', 'staff']
            ).order_by('-created_at')[:5],
        })

    # ──────────────────────────────────────────────
    # استاد — دروس، دانشجویان، تکالیف خودش
    # ──────────────────────────────────────────────
    elif role == 'professor':
        active_sem = Semester.objects.filter(is_active=True).first()
        my_assignments = TeachingAssignment.objects.filter(
            professor=user, is_active=True
        ).select_related('course', 'semester')
        if active_sem:
            my_assignments_this_sem = my_assignments.filter(semester=active_sem)
        else:
            my_assignments_this_sem = my_assignments[:5]

        # دانشجویان درس‌های این استاد
        course_ids = my_assignments.values_list('course_id', flat=True)
        my_students = Enrollment.objects.filter(
            course__in=course_ids, status__in=['registered', 'in_progress']
        ).select_related('student', 'course').distinct()

        # تکالیف این استاد
        my_assignments_obj = Assignment.objects.filter(
            professor=user, is_active=True
        ).order_by('-due_date')[:5]

        # درخواست‌های دانشجویی در انتظار
        pending_req = StudentRequest.objects.filter(status='pending').count()

        context.update({
            'page_title': 'داشبورد استاد',
            'active_semester': active_sem,
            'my_courses': my_assignments_this_sem,
            'total_my_courses': my_assignments.count(),
            'total_my_students': my_students.count(),
            'my_students': my_students[:6],
            'my_assignments': my_assignments_obj,
            'pending_student_requests': pending_req,
            'announcements': Announcement.objects.filter(
                is_active=True, target__in=['all', 'professors']
            ).order_by('-created_at')[:5],
            'recent_news': News.objects.filter(is_published=True).order_by('-published_at')[:4],
        })

    # ──────────────────────────────────────────────
    # دانشجو — دروس، نمرات، درخواست‌ها، امتحانات
    # ──────────────────────────────────────────────
    else:  # student
        active_sem = Semester.objects.filter(is_active=True).first()
        my_enrollments = Enrollment.objects.filter(
            student=user
        ).select_related('course', 'semester').order_by('-enrolled_at')

        if active_sem:
            current_enrollments = my_enrollments.filter(semester=active_sem)
        else:
            current_enrollments = my_enrollments

        # نمرات این ترم — قبل از slice فیلتر می‌کنیم
        graded = current_enrollments.filter(final_grade__isnull=False)

        # امتحانات پیش‌رو — قبل از slice فیلتر می‌کنیم
        upcoming_exams = ExamSchedule.objects.filter(
            course__in=current_enrollments.values_list('course_id', flat=True),
            date__gte=timezone.now().date()
        ).order_by('date', 'start_time')[:5]

        # حالا که فیلترها تمام شد، slice می‌زنیم
        current_enrollments = current_enrollments[:6]

        # درخواست‌های دانشجویی
        my_requests = StudentRequest.objects.filter(
            student=user
        ).order_by('-created_at')[:5]

        # پرداخت‌ها
        my_payments = Payment.objects.filter(
            student=user
        ).order_by('-created_at')[:3]

        # تکالیف در انتظار تحویل
        enrolled_course_ids = current_enrollments.values_list('course_id', flat=True)
        pending_assignments = Assignment.objects.filter(
            course__in=enrolled_course_ids,
            is_active=True,
            due_date__gte=timezone.now()
        ).order_by('due_date')[:5]

        context.update({
            'page_title': 'داشبورد دانشجو',
            'active_semester': active_sem,
            'current_enrollments': current_enrollments,
            'total_units': sum(e.course.credits for e in current_enrollments),
            'graded_count': graded.count(),
            'upcoming_exams': upcoming_exams,
            'my_requests': my_requests,
            'pending_requests_count': StudentRequest.objects.filter(student=user, status='pending').count(),
            'my_payments': my_payments,
            'pending_assignments': pending_assignments,
            'announcements': Announcement.objects.filter(
                is_active=True, target__in=['all', 'students']
            ).order_by('-created_at')[:5],
            'recent_news': News.objects.filter(is_published=True).order_by('-published_at')[:4],
        })

    return render(request, 'dashboard/dashboard.html', context)
