from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.conf import settings
from django.db.models import Q
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
    Enrollment,
    ExamSchedule,
    Payment,
    Semester,
    StudentRequest,
    TeachingAssignment,
)


def get_user_role(user):
    try:
        return user.profile.role
    except Exception:
        return 'student'


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


def student_enrollment_qs(user, semester=None):
    qs = Enrollment.objects.filter(student=user).select_related(
        'course', 'semester', 'course__major'
    ).order_by('-enrolled_at')
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

    if role == 'admin' or user.is_staff:
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
    active_sem = context['active_semester']
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


@role_required('student')
def student_grades(request):
    ctx = panel_context(request, 'نمرات و کارنامه', 'grades')
    enrollments = student_enrollment_qs(request.user).filter(
        Q(final_grade__isnull=False) | Q(mid_term_grade__isnull=False)
    ).distinct().order_by('-semester__start_date', 'course__name')

    # گروه‌بندی بر اساس ترم
    by_semester = {}
    for en in enrollments:
        key = en.semester_id
        if key not in by_semester:
            by_semester[key] = {'semester': en.semester, 'items': []}
        by_semester[key]['items'].append(en)

    # میانگین تقریبی (فقط نمرات نهایی)
    graded = [e for e in enrollments if e.final_grade is not None]
    avg = None
    if graded:
        total_w = sum(float(e.final_grade) * e.course.credits for e in graded)
        total_c = sum(e.course.credits for e in graded) or 1
        avg = round(total_w / total_c, 2)

    ctx.update({
        'by_semester': by_semester.values(),
        'grade_average': avg,
        'graded_count': len(graded),
    })
    return render(request, 'dashboard/student_grades.html', ctx)


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

    ctx.update({
        'form': form,
        'requests': StudentRequest.objects.filter(student=request.user).order_by('-created_at'),
    })
    return render(request, 'dashboard/student_requests.html', ctx)


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
            if timezone.now() > assignment.due_date:
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
    ctx = panel_context(request, 'پرداخت‌ها', 'payments')
    ctx['payments'] = Payment.objects.filter(student=request.user).order_by('-created_at')
    ctx['payment_gateway'] = getattr(settings, 'PAYMENT_GATEWAY', 'mock')
    return render(request, 'dashboard/student_payments.html', ctx)


@role_required('student')
def payment_start(request, pk):
    """شروع پرداخت آنلاین برای یک پرداخت در انتظار."""
    payment = get_object_or_404(Payment, pk=pk, student=request.user)
    if payment.status == 'paid':
        messages.info(request, 'این پرداخت قبلاً انجام شده است.')
        return redirect('dashboard:student_payments')
    if payment.status not in ('pending', 'failed'):
        messages.warning(request, 'امکان پرداخت این مورد وجود ندارد.')
        return redirect('dashboard:student_payments')

    payment.status = 'pending'
    payment.save(update_fields=['status'])

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

    if payment.student_id != request.user.id and not request.user.is_staff:
        messages.error(request, 'دسترسی غیرمجاز.')
        return redirect('dashboard:dashboard')

    if payment.status == 'paid':
        messages.success(request, 'پرداخت قبلاً تأیید شده است.')
        return redirect('dashboard:student_payments')

    try:
        ok = verify_payment(request, payment, authority=authority)
    except PaymentGatewayError as e:
        messages.error(request, str(e))
        return redirect('dashboard:student_payments')

    if ok:
        messages.success(
            request,
            f'پرداخت موفق — کد پیگیری: {payment.transaction_id or payment.authority}',
        )
    else:
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
