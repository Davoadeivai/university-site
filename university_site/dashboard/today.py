"""«کارهای امروز» — سه کار فوری دانشجو، مرتب بر اساس ضرب‌الاجل.

چرا
───
داشبورد دانشجو هشت جعبهٔ هم‌وزن دارد: درس‌ها، امتحانات، تکالیف،
پرداخت‌ها، درخواست‌ها، اطلاعیه‌ها… دانشجویی که سه روز دیگر قسط
سررسید دارد و فردا تکلیف تحویل می‌دهد، باید خودش این را از میان
جعبه‌ها دربیاورد. صفحه همه‌چیز را نشان می‌دهد و هیچ‌چیز را نمی‌گوید.

اینجا فقط کارهایی جمع می‌شوند که **ضرب‌الاجل دارند و هنوز انجام
نشده‌اند**، مرتب بر اساس نزدیک‌ترین مهلت. اگر چیزی نبود، فهرست خالی
برمی‌گردد و قالب اصلاً نوار را نمی‌کشد — نوار «همه‌چیز مرتب است»
فقط یک جعبهٔ دیگر است.

چه چیزهایی شمرده می‌شوند
────────────────────────
قسط سررسیدشده یا نزدیک، تکلیف تحویل‌نداده، امتحان نزدیک، و مرحلهٔ
بعدیِ مسیر ترم (انتخاب واحد و مانندش) که از `build_journey_status`
می‌آید.
"""
from __future__ import annotations

from datetime import date, timedelta

from django.urls import reverse
from django.utils import timezone

# چند روز مانده تا چیزی «فوری» حساب شود
PAYMENT_HORIZON = 10
EXAM_HORIZON = 7
ASSIGNMENT_HORIZON = 7

MAX_ITEMS = 3


def _days_word(days: int) -> str:
    if days < 0:
        return 'گذشته'
    if days == 0:
        return 'امروز'
    if days == 1:
        return 'فردا'
    return '%d روز مانده' % days


def _payments(user) -> list[dict]:
    from .models import Payment

    today = date.today()
    limit = today + timedelta(days=PAYMENT_HORIZON)
    rows = (
        Payment.objects
        .filter(student=user, status='pending', due_date__isnull=False,
                due_date__lte=limit)
        .order_by('due_date')[:MAX_ITEMS]
    )
    items = []
    for payment in rows:
        days = (payment.due_date - today).days
        items.append({
            'kind': 'payment',
            'icon': 'fa-credit-card',
            'tone': 'danger' if days <= 2 else 'warning',
            'title': payment.get_installment_stage_display() or 'شهریه',
            'note': '%s تومان' % f'{payment.amount:,}',
            'when': _days_word(days),
            'sort': days,
            'url': reverse('dashboard:student_payments'),
            'action': 'پرداخت',
        })
    return items


def _assignments(user, course_ids) -> list[dict]:
    from .models import Assignment, AssignmentSubmission

    if not course_ids:
        return []
    now = timezone.now()
    limit = now + timedelta(days=ASSIGNMENT_HORIZON)
    handed_in = set(
        AssignmentSubmission.objects
        .filter(student=user)
        .values_list('assignment_id', flat=True)
    )
    rows = (
        Assignment.objects
        .filter(course_id__in=course_ids, is_active=True,
                due_date__gte=now, due_date__lte=limit)
        .exclude(id__in=handed_in)
        .select_related('course')
        .order_by('due_date')[:MAX_ITEMS]
    )
    items = []
    for hw in rows:
        days = (hw.due_date.date() - now.date()).days
        items.append({
            'kind': 'assignment',
            'icon': 'fa-file-pen',
            'tone': 'danger' if days <= 1 else 'primary',
            'title': hw.title,
            'note': hw.course.name if hw.course_id else '',
            'when': _days_word(days),
            'sort': days,
            'url': reverse('dashboard:student_assignments'),
            'action': 'ارسال',
        })
    return items


def _exams(course_ids) -> list[dict]:
    from .models import ExamSchedule

    if not course_ids:
        return []
    today = date.today()
    limit = today + timedelta(days=EXAM_HORIZON)
    rows = (
        ExamSchedule.objects
        .filter(course_id__in=course_ids, date__gte=today, date__lte=limit)
        .select_related('course')
        .order_by('date', 'start_time')[:MAX_ITEMS]
    )
    items = []
    for exam in rows:
        days = (exam.date - today).days
        items.append({
            'kind': 'exam',
            'icon': 'fa-pen-to-square',
            'tone': 'danger' if days <= 1 else 'info',
            'title': 'امتحان %s' % (exam.course.name if exam.course_id else ''),
            'note': str(exam.start_time)[:5] if exam.start_time else '',
            'when': _days_word(days),
            'sort': days,
            'url': reverse('dashboard:student_exams'),
            'action': 'جزئیات',
        })
    return items


def _journey(journey) -> list[dict]:
    """مرحلهٔ بعدیِ مسیر ترم — اگر باز است و هنوز انجام نشده."""
    if not journey or not journey.get('next_url'):
        return []
    title = journey.get('next_title') or ''
    if not title:
        for step in journey.get('steps') or []:
            if not step.get('done') and not step.get('locked'):
                title = step.get('title') or ''
                break
    if not title:
        return []
    return [{
        'kind': 'journey',
        'icon': 'fa-arrow-left',
        'tone': 'success',
        'title': title,
        'note': 'مرحلهٔ بعدی ترم',
        'when': '',
        # بدون ضرب‌الاجل: بعد از کارهای تاریخ‌دار بنشیند، نه قبلشان
        'sort': 99,
        'url': journey['next_url'],
        'action': 'ادامه',
    }]


def build(user, course_ids=None, journey=None) -> list[dict]:
    """حداکثر سه کار فوری، مرتب‌شده. خالی یعنی نوار نمایش داده نشود."""
    course_ids = list(course_ids or [])
    items = (
        _payments(user)
        + _assignments(user, course_ids)
        + _exams(course_ids)
        + _journey(journey)
    )
    items.sort(key=lambda row: row['sort'])
    return items[:MAX_ITEMS]
