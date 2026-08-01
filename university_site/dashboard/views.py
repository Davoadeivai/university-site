from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.conf import settings
from django.db import models, transaction
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from accounts.models import Announcement
from admissions.models import Application
from contact.models import ContactMessage
from news.models import News

from .forms import (
    AssignmentForm,
    AssignmentSubmissionForm,
    EnrollmentGradeForm,
    StaffRequestResponseForm,
    StudentRequestForm,
    SubmissionGradeForm,
)
from .models import (
    Assignment,
    AssignmentSubmission,
    Attendance,
    Enrollment,
    ExamSchedule,
    Payment,
    Semester,
    StudentDiscountClaim,
    StudentRequest,
    TeachingAssignment,
)


def get_user_role(user):
    try:
        return user.profile.role
    except Exception:
        return None


def role_required(*roles):
    """اجازه دسترسی فقط برای نقش‌های مشخص‌شده."""
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            role = get_user_role(request.user)
            if role == 'admin' or request.user.is_staff:
                # ادمین به پنل‌های مدیریتی دسترسی دارد
                if 'staff' in roles or 'admin' in roles:
                    return view_func(request, *args, **kwargs)
            if role not in roles:
                if 'student' in roles and role in ('admin', 'staff'):
                    from django.utils.http import urlencode
                    messages.warning(
                        request,
                        'این بخش مخصوص دانشجو است. با حساب دانشجویی وارد شوید.',
                    )
                    q = urlencode({'next': request.get_full_path(), 'as_student': '1'})
                    return redirect(f'/accounts/login/?{q}')
                messages.error(request, 'شما به این بخش دسترسی ندارید.')
                return redirect('dashboard:dashboard')
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


def panel_context(request, page_title, active_nav):
    role = get_user_role(request.user)
    return {
        'role': role,
        'page_title': page_title,
        'active_nav': active_nav,
        'is_panel': True,
        'active_semester': Semester.objects.filter(is_active=True).first(),
    }


def professor_teaching_qs(user):
    return TeachingAssignment.objects.filter(
        professor=user, is_active=True
    ).select_related('course', 'semester', 'department')


def student_enrollment_qs(user, semester=None, include_dropped=False):
    qs = Enrollment.objects.filter(student=user).select_related(
        'course', 'semester', 'course__major', 'teaching_assignment',
    ).order_by('-enrolled_at')
    if not include_dropped:
        qs = qs.exclude(status='dropped')
    if semester:
        qs = qs.filter(semester=semester)
    return qs


# ──────────────────────────────────────────────
# داشبورد اصلی (نمای کلی)
# ──────────────────────────────────────────────
@login_required
def dashboard(request):
    user = request.user
    role = get_user_role(user)
    context = panel_context(request, 'داشبورد', 'home')
    context['role'] = role

    if role == 'admin' or user.is_superuser:
        context.update({
            'page_title': 'داشبورد ادمین',
            'is_panel': False,
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
        return render(request, 'dashboard/dashboard.html', context)

    if role == 'staff':
        context.update({
            'page_title': 'داشبورد مدیریت دانشگاه',
            'is_panel': True,
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
        return render(request, 'dashboard/dashboard.html', context)

    if role == 'professor':
        active_sem = context['active_semester']
        my_teaching = professor_teaching_qs(user)
        my_courses = my_teaching.filter(semester=active_sem) if active_sem else my_teaching[:8]
        course_ids = list(my_teaching.values_list('course_id', flat=True))
        my_students = Enrollment.objects.filter(
            course_id__in=course_ids, status__in=['registered', 'in_progress']
        ).select_related('student', 'course').distinct()
        my_hw = Assignment.objects.filter(professor=user, is_active=True).order_by('-due_date')[:5]
        ungraded = AssignmentSubmission.objects.filter(
            assignment__professor=user, status='submitted'
        ).count()

        context.update({
            'page_title': 'پنل استاد',
            'my_courses': my_courses,
            'total_my_courses': my_teaching.count(),
            'total_my_students': my_students.count(),
            'my_students': my_students[:6],
            'my_assignments': my_hw,
            'ungraded_submissions': ungraded,
            'announcements': Announcement.objects.filter(
                is_active=True, target__in=['all', 'professors']
            ).order_by('-created_at')[:5],
        })
        return render(request, 'dashboard/professor_home.html', context)

    # دانشجو
    from .onboarding import build_journey_status, ensure_tuition_invoice
    active_sem = context['active_semester']
    ensure_tuition_invoice(user, active_sem)
    context['journey'] = build_journey_status(user=user)
    journey = context['journey']
    profile = getattr(user, 'profile', None)
    terminal = bool(journey and journey.get('terminal_status'))

    if terminal:
        context.update({
            'page_title': 'پنل دانشجو',
            'terminal_status': True,
            'academic_status': journey.get('academic_status'),
            'academic_status_display': (
                profile.get_academic_status_display() if profile else ''
            ),
            'status_note': getattr(profile, 'status_note', '') if profile else '',
            'clearance': journey.get('clearance'),
            'lifecycle_requests': journey.get('lifecycle_requests') or [],
            'current_enrollments': [],
            'enrollment_count': 0,
            'total_units': 0,
            'graded_count': 0,
            'upcoming_exams': [],
            'my_requests': [],
            'pending_requests_count': 0,
            'my_payments': Payment.objects.filter(student=user).order_by('-created_at')[:3],
            'pending_assignments': [],
            'announcements': Announcement.objects.filter(
                is_active=True, target__in=['all', 'students']
            ).order_by('-created_at')[:5],
        })
        return render(request, 'dashboard/student_home.html', context)

    all_current = student_enrollment_qs(user, active_sem) if active_sem else student_enrollment_qs(user)
    course_ids = list(all_current.values_list('course_id', flat=True))
    graded = all_current.filter(final_grade__isnull=False)
    upcoming_exams = ExamSchedule.objects.filter(
        course_id__in=course_ids,
        date__gte=timezone.now().date(),
    ).select_related('course').order_by('date', 'start_time')[:5]
    pending_assignments = Assignment.objects.filter(
        course_id__in=course_ids,
        is_active=True,
        due_date__gte=timezone.now(),
    ).select_related('course').order_by('due_date')[:5]
    my_requests = StudentRequest.objects.filter(student=user).order_by('-created_at')[:5]
    my_payments = Payment.objects.filter(student=user).order_by('-created_at')[:3]

    context.update({
        'page_title': 'پنل دانشجو',
        'terminal_status': False,
        'academic_status': journey.get('academic_status') if journey else 'active',
        'academic_status_display': (
            profile.get_academic_status_display() if profile else 'در حال تحصیل'
        ),
        'clearance': journey.get('clearance') if journey else None,
        'current_enrollments': all_current[:8],
        'enrollment_count': all_current.count(),
        'total_units': sum(e.course.credits for e in all_current),
        'graded_count': graded.count(),
        'upcoming_exams': upcoming_exams,
        'my_requests': my_requests,
        'pending_requests_count': StudentRequest.objects.filter(
            student=user, status='pending'
        ).count(),
        'my_payments': my_payments,
        'pending_assignments': pending_assignments,
        'announcements': Announcement.objects.filter(
            is_active=True, target__in=['all', 'students']
        ).order_by('-created_at')[:5],
    })
    return render(request, 'dashboard/student_home.html', context)


# ──────────────────────────────────────────────
# پنل دانشجو
# ──────────────────────────────────────────────
@role_required('student')
def student_courses(request):
    ctx = panel_context(request, 'دروس من', 'courses')
    active_sem = ctx['active_semester']
    enrollments = student_enrollment_qs(request.user)
    current = enrollments.filter(semester=active_sem) if active_sem else enrollments
    ctx.update({
        'current_enrollments': current,
        'all_enrollments': enrollments,
        'total_units': sum(e.course.credits for e in current),
    })
    return render(request, 'dashboard/student_courses.html', ctx)


MAX_REGISTRATION_UNITS = 24


@role_required('student')
def student_registration(request):
    """انتخاب واحد + انتخاب استاد/کلاس (در صورت چند ارائه)."""
    from collections import defaultdict
    from academics.models import Course
    from .enrollment_rules import can_enroll, check_final_submission, get_standing
    from .onboarding import ensure_tuition_invoice, sync_profile_from_application, tuition_first_paid

    ctx = panel_context(request, 'انتخاب واحد', 'registration')
    semester = ctx['active_semester']
    profile = sync_profile_from_application(request.user)
    ensure_tuition_invoice(request.user, semester)
    paid = tuition_first_paid(request.user, semester)

    if getattr(profile, 'academic_status', 'active') in ('graduated', 'withdrawn', 'expelled', 'leave'):
        messages.warning(
            request,
            'با وضعیت تحصیلی فعلی امکان انتخاب واحد وجود ندارد.',
        )
        return redirect('dashboard:dashboard')
    if not semester:
        messages.warning(request, 'ترم فعالی تعریف نشده است.')
        return redirect('dashboard:dashboard')
    if not semester.registration_open:
        messages.warning(request, 'بازه انتخاب واحد این ترم بسته است.')
        return redirect('dashboard:student_courses')
    if not paid:
        messages.error(request, 'قبل از انتخاب واحد، قسط اول شهریه را پرداخت کنید.')
        return redirect('dashboard:student_payments')
    if not profile.major_id:
        messages.error(
            request,
            'رشته تحصیلی در پروفایل شما تنظیم نشده است. '
            'با دفتر آموزش تماس بگیرید تا رشته را ثبت کنند.',
        )
        return redirect('dashboard:dashboard')

    offerings = list(
        TeachingAssignment.objects.filter(
            semester=semester, is_active=True, course__major=profile.major
        ).select_related('course', 'professor')
    )
    offerings_by_course = defaultdict(list)
    for o in offerings:
        offerings_by_course[o.course_id].append(o)

    # همه دروس رشته + کلاس‌های تعریف‌شده (دروس بدون کلاس هم دیده شوند)
    courses = list(Course.objects.filter(major=profile.major).order_by('semester', 'name'))

    current = student_enrollment_qs(request.user, semester).select_related(
        'course', 'teaching_assignment'
    )
    enrolled_map = {e.course_id: e for e in current}
    total_units = sum(e.course.credits for e in current)

    if request.method == 'POST':
        if not semester.registration_open:
            messages.warning(request, 'بازه انتخاب واحد این ترم بسته است.')
            return redirect('dashboard:student_courses')
        if not tuition_first_paid(request.user, semester):
            messages.error(request, 'قبل از انتخاب واحد، قسط اول شهریه را پرداخت کنید.')
            return redirect('dashboard:student_payments')
        if not profile.major_id:
            return redirect('dashboard:dashboard')
        action = request.POST.get('action')
        course_id = request.POST.get('course_id')
        course = get_object_or_404(Course, pk=course_id, major=profile.major)
        if action == 'enroll':
            with transaction.atomic():
                locked = list(
                    Enrollment.objects.select_for_update().filter(
                        student=request.user, semester=semester
                    ).exclude(status='dropped').select_related('course')
                )
                locked_map = {e.course_id: e for e in locked}
                units_now = sum(e.course.credits for e in locked)
                if course.id in locked_map:
                    messages.info(request, 'این درس قبلاً انتخاب شده است.')
                else:
                    ta = None
                    ta_id = request.POST.get('teaching_assignment_id')
                    opts = offerings_by_course.get(course.id) or []
                    if ta_id:
                        ta = next((x for x in opts if str(x.id) == str(ta_id)), None)
                        if ta is None:
                            messages.error(request, 'کلاس/استاد انتخاب‌شده معتبر نیست.')
                            return redirect('dashboard:student_registration')
                    elif len(opts) == 1:
                        ta = opts[0]
                    elif len(opts) > 1:
                        messages.error(request, 'لطفاً استاد / کلاس مورد نظر را انتخاب کنید.')
                        return redirect('dashboard:student_registration')

                    # آیین‌نامه: پیش‌نیاز، هم‌نیاز، درس گذرانده، سقف واحد،
                    # ظرفیت کلاس و تداخل ساعت — همه داخل همان قفل تراکنش
                    problems = can_enroll(
                        request.user, course, semester, ta, units_now,
                        standing=get_standing(request.user, semester),
                    )
                    if problems:
                        for p in problems:
                            messages.error(request, p)
                        return redirect('dashboard:student_registration')

                    Enrollment.objects.update_or_create(
                        student=request.user,
                        course=course,
                        semester=semester,
                        defaults={
                            'status': 'registered',
                            'teaching_assignment': ta,
                            'mid_term_grade': None,
                            'final_grade': None,
                            'attendance_score': None,
                        },
                    )
                    messages.success(request, f'درس «{course.name}» انتخاب شد.')
        elif action == 'drop':
            en = Enrollment.objects.filter(
                student=request.user, course=course, semester=semester
            ).exclude(status='dropped').first()
            if en:
                en.status = 'dropped'
                en.teaching_assignment = None
                en.mid_term_grade = None
                en.final_grade = None
                en.attendance_score = None
                en.save()
                messages.success(request, f'درس «{course.name}» حذف شد.')
        return redirect('dashboard:student_registration')

    standing = get_standing(request.user, semester)

    rows = []
    for course in courses:
        opts = offerings_by_course.get(course.id) or []
        en = enrolled_map.get(course.id)
        primary = None
        if en and en.teaching_assignment_id:
            primary = en.teaching_assignment
        elif len(opts) == 1:
            primary = opts[0]

        # دلیل غیرقابل‌انتخاب بودن را همین‌جا نشان بده، نه بعد از کلیک
        blockers = []
        if en is None:
            blockers = can_enroll(
                request.user, course, semester,
                primary if len(opts) == 1 else None,
                total_units, standing=standing,
            )

        rows.append({
            'course': course,
            'enrolled': en is not None,
            'enrollment': en,
            'offerings': opts,
            'blockers': blockers,
            'blocked': bool(blockers),
            'professor': primary.professor if primary else None,
            'schedule': primary.schedule_display() if primary else '',
            'classroom': primary.classroom if primary else '',
            'seats_left': primary.remaining_seats if primary else None,
        })

    ctx.update({
        'rows': rows,
        'total_units': total_units,
        'max_units': standing.max_units,
        'min_units': standing.min_units,
        'standing': standing,
        'submission_issues': check_final_submission(request.user, semester, standing),
        'major': profile.major,
        'semester': semester,
    })
    return render(request, 'dashboard/student_registration.html', ctx)


@role_required('student')
def student_schedule(request):
    """برنامه کلاس و لیست استاد برای دروس انتخاب‌شده."""
    ctx = panel_context(request, 'برنامه کلاس و اساتید', 'schedule')
    semester = ctx['active_semester']
    enrollments = (
        student_enrollment_qs(request.user, semester) if semester else student_enrollment_qs(request.user)
    ).exclude(status='dropped').select_related('teaching_assignment', 'teaching_assignment__professor', 'course')
    course_ids = list(enrollments.values_list('course_id', flat=True))
    ta_qs = TeachingAssignment.objects.filter(course_id__in=course_ids, is_active=True)
    if semester:
        ta_qs = ta_qs.filter(semester=semester)
    fallback = {ta.course_id: ta for ta in ta_qs.select_related('professor', 'course')}

    rows = []
    for en in enrollments:
        ta = en.teaching_assignment or fallback.get(en.course_id)
        rows.append({
            'enrollment': en,
            'course': en.course,
            'professor': ta.professor if ta else None,
            'schedule': ta.class_schedule if ta else '',
            'classroom': ta.classroom if ta else '',
        })
    ctx['rows'] = rows
    ctx['semester'] = semester
    return render(request, 'dashboard/student_schedule.html', ctx)


@role_required('student')
def student_exam_card(request):
    """کارت ورود به جلسه — فقط پس از تسویه کامل شهریه."""
    from .barcode import barcode_svg
    from .onboarding import (
        ensure_exam_barcode,
        sync_profile_from_application,
        tuition_fully_settled,
        tuition_summary,
    )

    ctx = panel_context(request, 'کارت ورود به جلسه', 'exam_card')
    semester = ctx['active_semester']
    profile = sync_profile_from_application(request.user)
    summary = tuition_summary(request.user, semester)
    settled = tuition_fully_settled(request.user, semester)
    enrollments = (
        student_enrollment_qs(request.user, semester) if semester else student_enrollment_qs(request.user)
    ).exclude(status='dropped')
    course_ids = list(enrollments.values_list('course_id', flat=True))
    exams = ExamSchedule.objects.filter(course_id__in=course_ids).select_related('course')
    if semester:
        exams = exams.filter(semester=semester)
    exams = exams.order_by('date', 'start_time')

    barcode_code = ''
    barcode_svg_markup = ''
    if settled and enrollments.exists():
        barcode_code = ensure_exam_barcode(request.user, semester)
        if barcode_code:
            barcode_svg_markup = barcode_svg(barcode_code)

    ctx.update({
        'settled': settled,
        'summary': summary,
        'profile': profile,
        'exams': exams,
        'enrollments': enrollments,
        'semester': semester,
        'can_issue': settled and enrollments.exists(),
        'barcode_code': barcode_code,
        'barcode_svg': barcode_svg_markup,
    })
    return render(request, 'dashboard/student_exam_card.html', ctx)


@role_required('student')
def print_tuition_receipt(request, pk=None):
    """پرینت رسید شهریه پرداخت‌شده."""
    from .onboarding import tuition_summary
    ctx = panel_context(request, 'رسید شهریه', 'payments')
    semester = ctx['active_semester']
    if pk:
        payments = list(Payment.objects.filter(pk=pk, student=request.user, status='paid'))
    else:
        payments = [p for p in tuition_summary(request.user, semester)['payments'] if p.status == 'paid']
    if not payments:
        messages.warning(request, 'رسید پرداخت‌شده‌ای برای پرینت وجود ندارد.')
        return redirect('dashboard:student_payments')
    ctx.update({
        'payments': payments,
        'print_mode': True,
        'student': request.user,
        'semester': semester,
    })
    return render(request, 'dashboard/print_tuition_receipt.html', ctx)


@role_required('student')
def print_class_schedule(request):
    """پرینت برنامه کلاسی دانشجو."""
    request.GET  # keep
    # reuse schedule data
    semester = Semester.objects.filter(is_active=True).first()
    enrollments = (
        student_enrollment_qs(request.user, semester) if semester else student_enrollment_qs(request.user)
    ).exclude(status='dropped').select_related('teaching_assignment', 'teaching_assignment__professor', 'course')
    course_ids = list(enrollments.values_list('course_id', flat=True))
    ta_qs = TeachingAssignment.objects.filter(course_id__in=course_ids, is_active=True)
    if semester:
        ta_qs = ta_qs.filter(semester=semester)
    fallback = {ta.course_id: ta for ta in ta_qs.select_related('professor')}
    rows = []
    for en in enrollments:
        ta = en.teaching_assignment or fallback.get(en.course_id)
        rows.append({
            'course': en.course,
            'professor': ta.professor if ta else None,
            'schedule': ta.class_schedule if ta else '',
            'classroom': ta.classroom if ta else '',
        })
    return render(request, 'dashboard/print_class_schedule.html', {
        **panel_context(request, 'پرینت برنامه کلاس', 'schedule'),
        'rows': rows,
        'semester': semester,
        'student': request.user,
        'print_mode': True,
    })


@role_required('professor')
def professor_print_roster(request, pk):
    """پرینت لیست دانشجویان کلاس برای استاد."""
    ta = get_object_or_404(
        TeachingAssignment.objects.select_related('course', 'semester'),
        pk=pk, professor=request.user, is_active=True,
    )
    enrollments = Enrollment.objects.filter(
        course=ta.course, semester=ta.semester
    ).exclude(status='dropped').select_related('student', 'student__profile').order_by(
        'student__last_name', 'student__first_name'
    )
    # اگر دانشجو این TA را انتخاب کرده باشد اولویت با همان است
    preferred = enrollments.filter(teaching_assignment=ta)
    if preferred.exists():
        enrollments = preferred
    return render(request, 'dashboard/print_professor_roster.html', {
        **panel_context(request, 'پرینت لیست کلاس', 'teaching'),
        'teaching': ta,
        'enrollments': enrollments,
        'print_mode': True,
    })


@role_required('student')
def student_grades(request):
    from .onboarding import tuition_fully_settled, tuition_summary

    ctx = panel_context(request, 'نمرات و کارنامه', 'grades')
    semester = ctx['active_semester']
    settled = tuition_fully_settled(request.user, semester)
    summary = tuition_summary(request.user, semester)

    if not settled:
        ctx.update({
            'grades_locked': True,
            'tuition_summary': summary,
            'by_semester': [],
            'grade_average': None,
            'graded_count': 0,
        })
        return render(request, 'dashboard/student_grades.html', ctx)

    # فقط ترم‌هایی که شهریه‌شان تسویه شده
    enrollments = student_enrollment_qs(request.user).filter(
        Q(final_grade__isnull=False) | Q(mid_term_grade__isnull=False)
    ).distinct().order_by('-semester__start_date', 'course__name')

    by_semester = {}
    for en in enrollments:
        if not tuition_fully_settled(request.user, en.semester):
            continue
        key = en.semester_id
        if key not in by_semester:
            by_semester[key] = {'semester': en.semester, 'items': []}
        by_semester[key]['items'].append(en)

    no_grades_yet = not by_semester

    graded = [e for e in enrollments if e.final_grade is not None]
    avg = None
    if graded:
        total_w = sum(float(e.final_grade) * e.course.credits for e in graded)
        total_c = sum(e.course.credits for e in graded) or 1
        avg = round(total_w / total_c, 2)

    from .enrollment_rules import get_standing

    ctx.update({
        'grades_locked': False,
        'no_grades_yet': no_grades_yet,
        'tuition_summary': summary,
        'by_semester': by_semester.values(),
        'grade_average': avg,
        'graded_count': len(graded),
        'standing': get_standing(request.user, semester),
    })
    return render(request, 'dashboard/student_grades.html', ctx)


@role_required('student')
def print_transcript(request):
    """کارنامهٔ رسمی نمرات، قابل چاپ — فقط پس از تسویهٔ کامل شهریه."""
    from .enrollment_rules import get_standing
    from .onboarding import tuition_fully_settled

    ctx = panel_context(request, 'کارنامه رسمی', 'grades')
    semester = ctx['active_semester']
    if not tuition_fully_settled(request.user, semester):
        messages.error(request, 'کارنامه پس از تسویهٔ کامل شهریه صادر می‌شود.')
        return redirect('dashboard:student_payments')

    enrollments = (
        student_enrollment_qs(request.user)
        .filter(final_grade__isnull=False)
        .select_related('course', 'semester', 'teaching_assignment__professor')
        .order_by('semester__start_date', 'course__name')
    )

    by_semester = {}
    for en in enrollments:
        if not tuition_fully_settled(request.user, en.semester):
            continue
        key = en.semester_id
        if key not in by_semester:
            by_semester[key] = {'semester': en.semester, 'items': [], 'units': 0,
                                'weighted': 0.0}
        blk = by_semester[key]
        blk['items'].append(en)
        blk['units'] += en.course.credits
        blk['weighted'] += float(en.final_grade) * en.course.credits
    for blk in by_semester.values():
        blk['gpa'] = round(blk['weighted'] / blk['units'], 2) if blk['units'] else None

    from core.models import SiteSettings
    return render(request, 'dashboard/print_transcript.html', {
        **ctx,
        'site': SiteSettings.objects.first(),
        'by_semester': list(by_semester.values()),
        'standing': get_standing(request.user, semester),
        'student': request.user,
        'profile': getattr(request.user, 'profile', None),
    })


@role_required('student')
def student_requests(request):
    ctx = panel_context(request, 'درخواست‌های من', 'requests')
    if request.method == 'POST':
        form = StudentRequestForm(request.POST, request.FILES)
        if form.is_valid():
            req = form.save(commit=False)
            req.student = request.user
            req.save()
            messages.success(request, 'درخواست شما ثبت شد.')
            return redirect('dashboard:student_requests')
    else:
        form = StudentRequestForm()

    # فرم رسمی هر نوع درخواست، کنار همان گزینه نشان داده می‌شود
    forms_map = StudentRequest.official_forms_map()
    ctx.update({
        'form': form,
        'requests': StudentRequest.objects.filter(student=request.user).order_by('-created_at'),
        'official_forms': [
            {'key': key,
             'label': dict(StudentRequest.REQUEST_TYPE_CHOICES).get(key, key),
             'doc': doc}
            for key, doc in forms_map.items()
        ],
    })
    return render(request, 'dashboard/student_requests.html', ctx)


@role_required('student')
def student_clearance(request):
    """پیشرفت چک‌لیست تسویه پایان‌تحصیل."""
    from .onboarding import get_or_create_clearance

    ctx = panel_context(request, 'تسویه پایان‌تحصیل', 'clearance')
    clearance = get_or_create_clearance(request.user)
    items = list(clearance.items.all())
    done = sum(1 for i in items if i.status in ('cleared', 'waived'))
    total = len(items) or 1
    ctx.update({
        'clearance': clearance,
        'items': items,
        'progress_pct': int(round(100 * done / total)),
    })
    return render(request, 'dashboard/student_clearance.html', ctx)


@role_required('student')
def student_lifecycle(request):
    """ثبت و پیگیری درخواست فارغ‌التحصیلی / انصراف / مرخصی."""
    from .models import StudentLifecycleRequest
    from .onboarding import get_or_create_clearance

    ctx = panel_context(request, 'پایان مسیر تحصیلی', 'lifecycle')
    profile = getattr(request.user, 'profile', None)
    academic_status = getattr(profile, 'academic_status', 'active') if profile else 'active'
    clearance = get_or_create_clearance(request.user)
    existing = StudentLifecycleRequest.objects.filter(student=request.user).order_by('-created_at')

    if request.method == 'POST':
        action = (request.POST.get('action') or 'submit').strip()
        if action == 'cancel':
            pk = request.POST.get('request_id')
            req = existing.filter(
                pk=pk, status__in=('draft', 'submitted')
            ).first()
            if req:
                req.status = 'cancelled'
                req.save(update_fields=['status', 'updated_at'])
                messages.info(request, 'درخواست لغو شد.')
            return redirect('dashboard:student_lifecycle')

        req_type = (request.POST.get('request_type') or '').strip()
        reason = (request.POST.get('reason') or '').strip()
        valid_types = {c[0] for c in StudentLifecycleRequest.TYPE_CHOICES}
        if req_type not in valid_types:
            messages.error(request, 'نوع درخواست معتبر نیست.')
            return redirect('dashboard:student_lifecycle')
        if academic_status in ('graduated', 'withdrawn', 'expelled'):
            messages.warning(request, 'وضعیت تحصیلی شما نهایی است؛ درخواست جدید ثبت نمی‌شود.')
            return redirect('dashboard:student_lifecycle')
        open_exists = existing.filter(
            status__in=('draft', 'submitted', 'under_review')
        ).exists()
        if open_exists:
            messages.warning(request, 'یک درخواست باز دارید؛ تا تعیین وضعیت صبر کنید.')
            return redirect('dashboard:student_lifecycle')
        if req_type in ('graduation', 'withdrawal') and not clearance.is_complete:
            messages.warning(
                request,
                'برای فارغ‌التحصیلی یا انصراف، ابتدا تسویه باید تکمیل شود (یا همزمان توسط آموزش پیگیری شود). '
                'درخواست شما به‌عنوان «ارسال‌شده» ثبت می‌شود ولی تأیید نهایی منوط به تسویه است.',
            )

        req = StudentLifecycleRequest(
            student=request.user,
            request_type=req_type,
            reason=reason,
            status='submitted',
        )
        attachment = request.FILES.get('attachment')
        if attachment:
            req.attachment = attachment
        req.save()
        messages.success(request, 'درخواست ثبت شد و پس از بررسی آموزش اعمال می‌شود.')
        return redirect('dashboard:student_lifecycle')

    ctx.update({
        'academic_status': academic_status,
        'academic_status_display': (
            profile.get_academic_status_display() if profile else ''
        ),
        'clearance': clearance,
        'requests': existing,
        'type_choices': StudentLifecycleRequest.TYPE_CHOICES,
    })
    return render(request, 'dashboard/student_lifecycle.html', ctx)


@role_required('student')
def student_assignments(request):
    ctx = panel_context(request, 'تکالیف', 'assignments')
    course_ids = list(student_enrollment_qs(request.user).values_list('course_id', flat=True))
    assignments = Assignment.objects.filter(
        course_id__in=course_ids, is_active=True
    ).select_related('course', 'professor').order_by('-due_date')

    submissions = {
        s.assignment_id: s
        for s in AssignmentSubmission.objects.filter(
            student=request.user, assignment__in=assignments
        )
    }
    rows = [{'assignment': a, 'submission': submissions.get(a.id)} for a in assignments]
    ctx['rows'] = rows
    return render(request, 'dashboard/student_assignments.html', ctx)


@role_required('student')
def student_assignment_submit(request, pk):
    assignment = get_object_or_404(Assignment, pk=pk, is_active=True)
    enrolled = Enrollment.objects.filter(
        student=request.user, course=assignment.course
    ).exists()
    if not enrolled:
        raise Http404

    submission = AssignmentSubmission.objects.filter(
        assignment=assignment, student=request.user
    ).first()

    if request.method == 'POST':
        form = AssignmentSubmissionForm(request.POST, request.FILES, instance=submission)
        if form.is_valid():
            sub = form.save(commit=False)
            sub.assignment = assignment
            sub.student = request.user
            # #10: due_date ممکن است None باشد — بررسی None-safe
            if assignment.due_date and timezone.now() > assignment.due_date:
                sub.status = 'late'
            else:
                sub.status = 'submitted'
            sub.save()
            messages.success(request, 'تکلیف با موفقیت ارسال شد.')
            return redirect('dashboard:student_assignments')
    else:
        form = AssignmentSubmissionForm(instance=submission)

    ctx = panel_context(request, 'ارسال تکلیف', 'assignments')
    ctx.update({'assignment': assignment, 'form': form, 'submission': submission})
    return render(request, 'dashboard/student_assignment_submit.html', ctx)


@role_required('student')
def student_exams(request):
    ctx = panel_context(request, 'برنامه امتحانات', 'exams')
    course_ids = list(student_enrollment_qs(request.user).values_list('course_id', flat=True))
    exams = ExamSchedule.objects.filter(
        course_id__in=course_ids
    ).select_related('course', 'semester').order_by('date', 'start_time')
    ctx['exams'] = exams
    ctx['upcoming'] = exams.filter(date__gte=timezone.now().date())
    ctx['today'] = timezone.now().date()
    return render(request, 'dashboard/student_exams.html', ctx)


@role_required('student')
def student_payments(request):
    from core.models import BankAccount
    from .onboarding import tuition_summary

    ctx = panel_context(request, 'پرداخت‌ها', 'payments')
    semester = ctx['active_semester']
    summary = tuition_summary(request.user, semester)
    discounts = []
    if semester:
        discounts = list(
            StudentDiscountClaim.objects.filter(student=request.user, semester=semester)
            .order_by('-created_at')
        )
    # #18: فقط پرداخت‌های ترم فعال نمایش داده شود، نه تمام ترم‌ها
    payments_qs = Payment.objects.filter(student=request.user)
    if semester:
        payments_qs = payments_qs.filter(
            models.Q(semester=semester) | models.Q(semester__isnull=True)
        )
    ctx['payments'] = payments_qs.order_by('installment_no', '-created_at')
    ctx['tuition_summary'] = summary
    ctx['payment_gateway'] = getattr(settings, 'PAYMENT_GATEWAY', 'mock')
    ctx['bank_accounts'] = BankAccount.objects.filter(is_active=True)[:5]
    ctx['discount_claims'] = discounts
    ctx['discount_types'] = StudentDiscountClaim.DISCOUNT_CHOICES
    ctx['payment_methods'] = Payment.METHOD_CHOICES
    return render(request, 'dashboard/student_payments.html', ctx)


@role_required('student')
def payment_offline(request, pk):
    """ثبت پرداخت آفلاین: کارت‌به‌کارت، کارتخوان، فیش بانکی، نقدی، سایر."""
    payment = get_object_or_404(Payment, pk=pk, student=request.user)
    if payment.status == 'paid':
        messages.info(request, 'این قسط قبلاً پرداخت شده است.')
        return redirect('dashboard:student_payments')
    if payment.status == 'review':
        messages.info(request, 'رسید شما در صف تأیید امور مالی است.')
        return redirect('dashboard:student_payments')
    if payment.status not in ('pending', 'failed'):
        messages.warning(request, 'امکان ثبت این پرداخت وجود ندارد.')
        return redirect('dashboard:student_payments')

    offline_methods = {
        'card_to_card', 'pos', 'bank_deposit', 'cash', 'other',
    }
    if request.method == 'POST':
        method = (request.POST.get('method') or '').strip()
        if method not in offline_methods:
            messages.error(request, 'روش پرداخت نامعتبر است.')
            return redirect('dashboard:payment_offline', pk=pk)
        receipt_ref = (request.POST.get('receipt_ref') or '').strip()[:100]
        method_notes = (request.POST.get('method_notes') or '').strip()[:500]
        receipt = request.FILES.get('receipt_file')
        if method in ('card_to_card', 'bank_deposit') and not receipt_ref and not receipt:
            messages.error(request, 'برای کارت‌به‌کارت یا فیش بانکی، شماره پیگیری یا تصویر رسید لازم است.')
            return redirect('dashboard:payment_offline', pk=pk)

        # #4: پرداخت آفلاین با transaction.atomic تا آپلود فایل و تغییر status باهم انجام شود
        with transaction.atomic():
            payment.method = method
            payment.receipt_ref = receipt_ref
            payment.method_notes = method_notes
            if receipt:
                payment.receipt_file = receipt
            payment.status = 'review'
            payment.save()
        messages.success(
            request,
            'رسید ثبت شد و برای تأیید امور مالی ارسال گردید. پس از تأیید، وضعیت به «پرداخت شده» تغییر می‌کند.',
        )
        return redirect('dashboard:student_payments')

    from core.models import BankAccount
    ctx = panel_context(request, 'ثبت پرداخت آفلاین', 'payments')
    ctx.update({
        'payment': payment,
        'bank_accounts': BankAccount.objects.filter(is_active=True)[:5],
        'offline_methods': [
            c for c in Payment.METHOD_CHOICES if c[0] in offline_methods
        ],
    })
    return render(request, 'dashboard/payment_offline.html', ctx)


@role_required('student')
def tuition_discount_claim(request):
    """درخواست تخفیف خواهر/برادر یا ایثارگری روی شهریه ترم فعال."""
    semester = Semester.objects.filter(is_active=True).first()
    if not semester:
        messages.error(request, 'ترم فعالی تعریف نشده است.')
        return redirect('dashboard:student_payments')
    if request.method != 'POST':
        return redirect('dashboard:student_payments')

    dtype = (request.POST.get('discount_type') or '').strip()
    valid = {c[0] for c in StudentDiscountClaim.DISCOUNT_CHOICES}
    if dtype not in valid:
        messages.error(request, 'نوع تخفیف نامعتبر است.')
        return redirect('dashboard:student_payments')
    try:
        percent = int(request.POST.get('percent') or 10)
    except (TypeError, ValueError):
        percent = 10
    percent = max(1, min(percent, 50))
    notes = (request.POST.get('notes') or '').strip()[:1000]
    document = request.FILES.get('document')

    claim, created = StudentDiscountClaim.objects.get_or_create(
        student=request.user,
        semester=semester,
        discount_type=dtype,
        defaults={'percent': percent, 'notes': notes, 'document': document},
    )
    if not created:
        if claim.status == 'approved':
            messages.info(request, 'این تخفیف قبلاً تأیید شده است.')
            return redirect('dashboard:student_payments')
        claim.percent = percent
        claim.notes = notes
        claim.status = 'pending'
        # #19: فایل مدرک جدید همیشه آپدیت شود، نه فقط وقتی document ارسال شده
        if document:
            claim.document = document
        claim.save(update_fields=['percent', 'notes', 'status', 'document'] if document else ['percent', 'notes', 'status'])
        messages.success(request, 'درخواست تخفیف به‌روز و دوباره ارسال شد.')
    else:
        messages.success(request, 'درخواست تخفیف ثبت شد؛ پس از بررسی امور مالی اعمال می‌شود.')
    return redirect('dashboard:student_payments')


@role_required('student')
def payment_start(request, pk):
    """شروع پرداخت آنلاین برای یک پرداخت در انتظار."""
    if request.method != 'POST' and request.method != 'GET':
        return redirect('dashboard:student_payments')
    payment = get_object_or_404(Payment, pk=pk, student=request.user)
    if payment.status == 'paid':
        messages.info(request, 'این پرداخت قبلاً انجام شده است.')
        return redirect('dashboard:student_payments')
    if payment.status == 'review':
        messages.info(request, 'رسید شما در انتظار تأیید امور مالی است.')
        return redirect('dashboard:student_payments')
    if payment.status not in ('pending', 'failed'):
        messages.warning(request, 'امکان پرداخت این مورد وجود ندارد.')
        return redirect('dashboard:student_payments')
    if not payment.amount or payment.amount <= 0:
        messages.error(request, 'مبلغ این قسط برای پرداخت آنلاین معتبر نیست.')
        return redirect('dashboard:student_payments')

    # ترتیب اقساط: قبل از قسط n همه قبلی‌ها باید paid باشند
    if payment.installment_no and payment.installment_no > 1:
        earlier = Payment.objects.filter(
            student=request.user,
            payment_type='tuition',
            semester=payment.semester,
            installment_no__lt=payment.installment_no,
        ).exclude(status='paid')
        if earlier.exists():
            messages.warning(request, 'ابتدا اقساط قبلی را پرداخت یا تأیید کنید.')
            return redirect('dashboard:student_payments')

    payment.status = 'pending'
    payment.method = 'online'
    payment.save(update_fields=['status', 'method'])

    from .payment_gateway import PaymentGatewayError, start_payment
    try:
        result = start_payment(request, payment)
    except PaymentGatewayError as e:
        messages.error(request, str(e))
        return redirect('dashboard:student_payments')
    return redirect(result['redirect_url'])


@role_required('student')
def payment_mock(request, pk):
    """صفحه شبیه‌ساز درگاه (حالت mock)."""
    from .payment_gateway import _mock_allowed
    if not _mock_allowed():
        messages.error(request, 'درگاه آزمایشی در محیط عملیاتی غیرفعال است.')
        return redirect('dashboard:student_payments')
    payment = get_object_or_404(Payment, pk=pk, student=request.user)
    authority = request.GET.get('Authority', payment.authority)
    if request.method == 'POST':
        action = request.POST.get('action', 'ok')
        status = 'OK' if action == 'ok' else 'NOK'
        return redirect(
            reverse('dashboard:payment_callback')
            + f'?Authority={authority}&Status={status}&payment_id={payment.pk}'
        )
    ctx = panel_context(request, 'درگاه آزمایشی', 'payments')
    ctx.update({'payment': payment, 'authority': authority})
    return render(request, 'dashboard/payment_mock.html', ctx)


@login_required
def payment_callback(request):
    """بازگشت از درگاه (mock یا زرین‌پال)."""
    from .payment_gateway import PaymentGatewayError, verify_payment

    authority = request.GET.get('Authority', '')
    payment_id = request.GET.get('payment_id')
    payment = None
    if payment_id:
        payment = Payment.objects.filter(pk=payment_id, student=request.user).first()
    if not payment and authority:
        payment = Payment.objects.filter(authority=authority, student=request.user).first()
    if not payment:
        # زرین‌پال ممکن است بدون login session برگردد — جستجو با authority
        payment = Payment.objects.filter(authority=authority).first()

    if not payment:
        messages.error(request, 'پرداخت یافت نشد.')
        return redirect('dashboard:student_payments')

    # #29: Staff نباید بتواند پرداخت دانشجویان دیگر را مدیریت کند؛
    # callback درگاه (بدون login) تنها با authority معتبر مجاز است.
    if payment.student_id != request.user.id:
        messages.error(request, 'دسترسی غیرمجاز.')
        return redirect('dashboard:dashboard')

    if payment.status == 'paid':
        messages.success(request, 'پرداخت قبلاً تأیید شده است.')
        return redirect('dashboard:student_payments')

    # #3: verify_payment داخل select_for_update فراخوانی شود تا race condition رفع شود
    try:
        with transaction.atomic():
            locked = Payment.objects.select_for_update().get(pk=payment.pk)
            if locked.status == 'paid':
                messages.success(request, 'پرداخت قبلاً تأیید شده است.')
                return redirect('dashboard:student_payments')
            # verify_payment روی locked object فراخوانی می‌شود (داخل transaction)
            ok = verify_payment(request, locked, authority=authority)
    except PaymentGatewayError as e:
        messages.error(request, str(e))
        return redirect('dashboard:student_payments')

    if ok:
        from .onboarding import tuition_first_paid, tuition_fully_settled
        messages.success(
            request,
            f'پرداخت موفق — کد پیگیری: {locked.transaction_id or locked.authority}',
        )
        if tuition_fully_settled(request.user, locked.semester):
            messages.info(request, 'شهریه کامل تسویه شد؛ می‌توانید کارت ورود به جلسه را دریافت کنید.')
            return redirect('dashboard:student_exam_card')
        if tuition_first_paid(request.user, locked.semester):
            messages.info(request, 'قسط اول پرداخت شد؛ اکنون انتخاب واحد باز است.')
            return redirect('dashboard:student_registration')
        return redirect('dashboard:student_payments')
    messages.error(request, 'پرداخت ناموفق بود یا لغو شد.')
    return redirect('dashboard:student_payments')


# ──────────────────────────────────────────────
# پنل استاد
# ──────────────────────────────────────────────
@role_required('professor')
def professor_courses(request):
    ctx = panel_context(request, 'دروس تدریس', 'teaching')
    teaching = professor_teaching_qs(request.user)
    active_sem = ctx['active_semester']
    ctx.update({
        'teaching_list': teaching.filter(semester=active_sem) if active_sem else teaching,
        'all_teaching': teaching,
    })
    return render(request, 'dashboard/professor_courses.html', ctx)


@role_required('professor')
def professor_course_detail(request, pk):
    ta = get_object_or_404(
        TeachingAssignment.objects.select_related('course', 'semester'),
        pk=pk, professor=request.user, is_active=True,
    )
    enrollments = Enrollment.objects.filter(
        course=ta.course, semester=ta.semester
    ).select_related('student').order_by('student__last_name', 'student__username')

    ctx = panel_context(request, ta.course.name, 'teaching')
    ctx.update({
        'teaching': ta,
        'enrollments': enrollments,
        'student_count': enrollments.count(),
    })
    return render(request, 'dashboard/professor_course_detail.html', ctx)


@role_required('professor')
def professor_attendance(request, pk):
    """ثبت حضور و غیاب یک جلسه.

    مدل Attendance از قبل وجود داشت ولی هیچ راهی برای ثبتش از پنل استاد نبود
    و فقط از ادمین قابل استفاده بود.
    """
    from datetime import date as _date

    ta = get_object_or_404(
        TeachingAssignment.objects.select_related('course', 'semester'),
        pk=pk, professor=request.user, is_active=True,
    )
    enrollments = list(
        Enrollment.objects.filter(course=ta.course, semester=ta.semester)
        .exclude(status='dropped')
        .select_related('student')
        .order_by('student__last_name', 'student__username')
    )

    raw_date = (request.POST.get('session_date') or request.GET.get('date') or '').strip()
    try:
        session_date = _date.fromisoformat(raw_date) if raw_date else timezone.localdate()
    except ValueError:
        session_date = timezone.localdate()

    if request.method == 'POST':
        saved = 0
        with transaction.atomic():
            for en in enrollments:
                status = request.POST.get(f'status_{en.pk}')
                if status not in dict(Attendance.STATUS_CHOICES):
                    continue
                Attendance.objects.update_or_create(
                    enrollment=en, date=session_date,
                    defaults={'status': status,
                              'notes': (request.POST.get(f'note_{en.pk}') or '').strip()},
                )
                saved += 1
        messages.success(request, f'حضور و غیاب {saved} دانشجو برای {session_date} ثبت شد.')
        return redirect(
            f"{reverse('dashboard:professor_attendance', args=[ta.pk])}?date={session_date}"
        )

    existing = {
        a.enrollment_id: a
        for a in Attendance.objects.filter(
            enrollment__in=enrollments, date=session_date
        )
    }
    rows = [{'enrollment': en, 'record': existing.get(en.pk)} for en in enrollments]

    # خلاصهٔ غیبت هر دانشجو در کل ترم
    absent_counts = dict(
        Attendance.objects
        .filter(enrollment__in=enrollments, status='absent')
        .values_list('enrollment')
        .annotate(n=Count('id'))
    )
    for r in rows:
        r['absent_total'] = absent_counts.get(r['enrollment'].pk, 0)

    ctx = panel_context(request, f'حضور و غیاب — {ta.course.name}', 'teaching')
    ctx.update({
        'teaching': ta,
        'rows': rows,
        'session_date': session_date,
        'status_choices': Attendance.STATUS_CHOICES,
    })
    return render(request, 'dashboard/professor_attendance.html', ctx)


@role_required('professor')
def professor_grade_edit(request, enrollment_id):
    enrollment = get_object_or_404(
        Enrollment.objects.select_related('course', 'student', 'semester'),
        pk=enrollment_id,
    )
    owns = TeachingAssignment.objects.filter(
        professor=request.user,
        course=enrollment.course,
        semester=enrollment.semester,
        is_active=True,
    ).exists()
    if not owns:
        raise Http404

    if request.method == 'POST':
        form = EnrollmentGradeForm(request.POST, instance=enrollment)
        if form.is_valid():
            form.save()
            messages.success(request, 'نمره ذخیره شد.')
            ta = TeachingAssignment.objects.filter(
                professor=request.user,
                course=enrollment.course,
                semester=enrollment.semester,
            ).first()
            return redirect('dashboard:professor_course_detail', pk=ta.pk)
    else:
        form = EnrollmentGradeForm(instance=enrollment)

    ctx = panel_context(request, 'ثبت نمره', 'teaching')
    ctx.update({'form': form, 'enrollment': enrollment})
    return render(request, 'dashboard/professor_grade_edit.html', ctx)


@role_required('professor')
def professor_assignments(request):
    from academics.models import Course

    ctx = panel_context(request, 'مدیریت تکالیف', 'assignments')
    teaching = professor_teaching_qs(request.user)
    course_ids = list(teaching.values_list('course_id', flat=True))
    active_sem = ctx['active_semester']
    course_qs = Course.objects.filter(id__in=course_ids)

    if request.method == 'POST':
        form = AssignmentForm(request.POST, request.FILES)
        form.fields['course'].queryset = course_qs
        if form.is_valid():
            asgn = form.save(commit=False)
            asgn.professor = request.user
            asgn.semester = active_sem or (teaching.first().semester if teaching.exists() else None)
            if not asgn.semester:
                messages.error(request, 'ترمی برای ثبت تکلیف یافت نشد.')
                return redirect('dashboard:professor_assignments')
            asgn.save()
            messages.success(request, 'تکلیف ایجاد شد.')
            return redirect('dashboard:professor_assignments')
    else:
        form = AssignmentForm()
        form.fields['course'].queryset = course_qs

    assignments = Assignment.objects.filter(
        professor=request.user
    ).select_related('course', 'semester').order_by('-due_date')

    ctx.update({
        'form': form,
        'assignments': assignments,
        'has_courses': course_qs.exists(),
    })
    return render(request, 'dashboard/professor_assignments.html', ctx)


@role_required('professor')
def professor_submissions(request, pk):
    assignment = get_object_or_404(Assignment, pk=pk, professor=request.user)
    submissions = AssignmentSubmission.objects.filter(
        assignment=assignment
    ).select_related('student').order_by('-submitted_at')

    ctx = panel_context(request, f'تحویل‌ها — {assignment.title}', 'assignments')
    ctx.update({'assignment': assignment, 'submissions': submissions})
    return render(request, 'dashboard/professor_submissions.html', ctx)


@role_required('professor')
def professor_grade_submission(request, pk):
    submission = get_object_or_404(
        AssignmentSubmission.objects.select_related('assignment', 'student'),
        pk=pk,
        assignment__professor=request.user,
    )
    if request.method == 'POST':
        form = SubmissionGradeForm(request.POST, instance=submission)
        if form.is_valid():
            sub = form.save(commit=False)
            if sub.grade is not None and sub.status == 'submitted':
                sub.status = 'graded'
            sub.save()
            messages.success(request, 'نمره تکلیف ثبت شد.')
            return redirect('dashboard:professor_submissions', pk=submission.assignment_id)
    else:
        form = SubmissionGradeForm(instance=submission)

    ctx = panel_context(request, 'نمره‌دهی تکلیف', 'assignments')
    ctx.update({'form': form, 'submission': submission})
    return render(request, 'dashboard/professor_grade_submission.html', ctx)


# ──────────────────────────────────────────────
# پنل کارکنان — رسیدگی به درخواست‌ها
# ──────────────────────────────────────────────
@role_required('staff', 'admin')
def staff_requests(request):
    ctx = panel_context(request, 'درخواست‌های دانشجویی', 'requests')
    status_filter = request.GET.get('status', 'pending')
    qs = StudentRequest.objects.select_related('student').order_by('-created_at')
    if status_filter and status_filter != 'all':
        qs = qs.filter(status=status_filter)
    ctx.update({
        'requests': qs[:50],
        'status_filter': status_filter,
        'pending_count': StudentRequest.objects.filter(status='pending').count(),
    })
    return render(request, 'dashboard/staff_requests.html', ctx)


@role_required('staff', 'admin')
def staff_request_respond(request, pk):
    req = get_object_or_404(StudentRequest.objects.select_related('student'), pk=pk)
    if request.method == 'POST':
        form = StaffRequestResponseForm(request.POST, instance=req)
        if form.is_valid():
            form.save()
            messages.success(request, 'پاسخ ثبت شد.')
            return redirect('dashboard:staff_requests')
    else:
        form = StaffRequestResponseForm(instance=req)

    ctx = panel_context(request, 'پاسخ به درخواست', 'requests')
    ctx.update({'form': form, 'student_request': req})
    return render(request, 'dashboard/staff_request_respond.html', ctx)


@role_required('staff', 'admin')
def staff_student_export(request):
    """لیست دانشجویان بر اساس رشته — پیش‌نمایش و خروجی اکسل/ورد."""
    from accounts.models import UserProfile
    from academics.models import Major
    from dashboard.student_export import excel_response, word_response

    majors = Major.objects.filter(is_active=True).select_related('group', 'department').order_by('degree', 'name')
    major_id = (request.GET.get('major') or '').strip()
    degree = (request.GET.get('degree') or '').strip()
    download = (request.GET.get('download') or '').strip().lower()

    from core.degree_map import CANONICAL_DEGREES, hub_degree_label, major_degree_q, to_canonical_degree
    degree = to_canonical_degree(degree) if degree else ''

    # #32: یک queryset واحد — فیلتر major از طریق profile یا enrollment در یک مرحله
    base_qs = (
        UserProfile.objects.filter(role='student')
        .select_related('user', 'major', 'major__group', 'major__department')
        .order_by('user__last_name', 'user__first_name')
    )
    if degree:
        major_ids = Major.objects.filter(major_degree_q(degree)).values_list('pk', flat=True)
        base_qs = base_qs.filter(major_id__in=major_ids)
    if major_id:
        enrolled_user_ids = (
            Enrollment.objects.filter(course__major_id=major_id)
            .values_list('student_id', flat=True)
            .distinct()
        )
        students = base_qs.filter(
            models.Q(major_id=major_id) | models.Q(user_id__in=enrolled_user_ids)
        )
    else:
        students = base_qs

    selected_major = majors.filter(pk=major_id).first() if major_id else None

    title = 'لیست دانشجویان ثبت‌نام‌شده'
    if selected_major:
        title = f'لیست دانشجویان رشته {selected_major.name} ({selected_major.get_degree_display()})'
    elif degree:
        title = f'لیست دانشجویان مقطع {hub_degree_label(degree)}'

    from core.jalali import jalali_now_stamp
    stamp = jalali_now_stamp('%Y%m%d')
    # #34: export را در try/except بپوشانیم تا خطاهای کتابخانه 500 نشود
    if download == 'excel':
        try:
            return excel_response(list(students), filename=f'students_{stamp}.xlsx', title=title)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error('Excel export failed: %s', exc)
            messages.error(request, 'خطا در تهیه فایل اکسل. لطفاً دوباره تلاش کنید.')
            return redirect(request.get_full_path().replace('&download=excel', '').replace('?download=excel', ''))
    if download == 'word':
        try:
            return word_response(list(students), filename=f'students_{stamp}.docx', title=title)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error('Word export failed: %s', exc)
            messages.error(request, 'خطا در تهیه فایل ورد. لطفاً دوباره تلاش کنید.')
            return redirect(request.get_full_path().replace('&download=word', '').replace('?download=word', ''))

    degrees = CANONICAL_DEGREES
    ctx = panel_context(request, 'خروجی لیست دانشجویان', 'student_export')
    ctx.update({
        'majors': majors,
        'degrees': degrees,
        'selected_major_id': str(major_id) if major_id else '',
        'selected_degree': degree,
        'students': students[:500],
        'student_count': students.count(),
        'selected_major': selected_major,
        'export_title': title,
    })
    return render(request, 'dashboard/staff_student_export.html', ctx)
