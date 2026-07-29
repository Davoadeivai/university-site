"""موتور قوانین انتخاب واحد — آیین‌نامهٔ آموزشی در یک جا.

تا پیش از این انتخاب واحد فقط سقف واحد را چک می‌کرد؛ پیش‌نیاز، تداخل ساعت،
ظرفیت کلاس، مشروطی و درسِ گذرانده هیچ‌کدام بررسی نمی‌شدند. تمام آن قواعد
اینجا جمع شده‌اند تا هم ویو تمیز بماند و هم قابل تست باشند.

هر تابع بررسی یک لیست از پیام‌های خطا برمی‌گرداند (خالی = مجاز).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from django.conf import settings
from django.db.models import Q


def _cfg(name: str, default):
    return getattr(settings, name, default)


# ─────────────────────────────────────────────────────────────
#  وضعیت تحصیلی دانشجو
# ─────────────────────────────────────────────────────────────

@dataclass
class AcademicStanding:
    passed_units: int = 0
    total_required: int = 0
    cumulative_gpa: float | None = None
    last_semester_gpa: float | None = None
    is_probation: bool = False
    max_units: int = 20
    min_units: int = 12
    remaining_units: int = 0
    progress_percent: int = 0
    passed_course_ids: set = field(default_factory=set)


def get_standing(student, semester=None) -> AcademicStanding:
    """وضعیت تحصیلی: واحد گذرانده، معدل، مشروطی و سقف واحد مجاز."""
    from .models import Enrollment

    pass_mark = _cfg('PASSING_GRADE', 10)
    st = AcademicStanding(
        max_units=_cfg('MAX_REGISTRATION_UNITS', 20),
        min_units=_cfg('MIN_REGISTRATION_UNITS', 12),
    )

    graded = list(
        Enrollment.objects
        .filter(student=student, final_grade__isnull=False)
        .exclude(status='dropped')
        .select_related('course', 'semester')
    )

    # درسی که چند بار گرفته شده: آخرین نمره ملاک است
    latest_by_course: dict[int, object] = {}
    for en in sorted(graded, key=lambda e: (e.semester.start_date or e.enrolled_at.date(),)):
        latest_by_course[en.course_id] = en

    passed = [e for e in latest_by_course.values() if float(e.final_grade) >= pass_mark]
    st.passed_units = sum(e.course.credits for e in passed)
    st.passed_course_ids = {e.course_id for e in passed}

    if latest_by_course:
        tw = sum(float(e.final_grade) * e.course.credits for e in latest_by_course.values())
        tc = sum(e.course.credits for e in latest_by_course.values()) or 1
        st.cumulative_gpa = round(tw / tc, 2)

    # معدل آخرین ترمِ نمره‌خورده (مبنای مشروطی)
    if graded:
        last_sem = max(
            (e.semester for e in graded),
            key=lambda s: (s.start_date or s.pk),
        )
        sem_items = [e for e in graded if e.semester_id == last_sem.pk]
        if sem_items:
            tw = sum(float(e.final_grade) * e.course.credits for e in sem_items)
            tc = sum(e.course.credits for e in sem_items) or 1
            st.last_semester_gpa = round(tw / tc, 2)
            st.is_probation = st.last_semester_gpa < _cfg('PROBATION_GPA', 12)

    if st.is_probation:
        st.max_units = min(st.max_units, _cfg('PROBATION_MAX_UNITS', 14))

    try:
        major = student.profile.major
        st.total_required = getattr(major, 'total_credits', 0) or 0
    except Exception:
        st.total_required = 0

    if st.total_required:
        st.remaining_units = max(0, st.total_required - st.passed_units)
        st.progress_percent = min(100, round(st.passed_units * 100 / st.total_required))

    return st


# ─────────────────────────────────────────────────────────────
#  بررسی‌های تک‌درس
# ─────────────────────────────────────────────────────────────

def check_prerequisites(student, course, standing: AcademicStanding) -> list[str]:
    """آیا دروس پیش‌نیاز پاس شده‌اند؟"""
    errors = []
    try:
        prereqs = list(course.prereq_courses.all())
    except Exception:
        return errors
    missing = [c for c in prereqs if c.id not in standing.passed_course_ids]
    if missing:
        names = '، '.join(c.name for c in missing)
        errors.append(f'ابتدا باید این پیش‌نیازها را بگذرانید: {names}')
    return errors


def check_corequisites(student, course, semester, standing: AcademicStanding) -> list[str]:
    """هم‌نیاز: یا قبلاً پاس شده یا همین ترم انتخاب شده باشد."""
    from .models import Enrollment

    errors = []
    try:
        coreqs = list(course.coreq_courses.all())
    except Exception:
        return errors
    if not coreqs:
        return errors

    taking_now = set(
        Enrollment.objects
        .filter(student=student, semester=semester)
        .exclude(status='dropped')
        .values_list('course_id', flat=True)
    )
    missing = [
        c for c in coreqs
        if c.id not in standing.passed_course_ids and c.id not in taking_now
    ]
    if missing:
        names = '، '.join(c.name for c in missing)
        errors.append(f'این دروس باید هم‌زمان یا پیش از این درس گرفته شوند: {names}')
    return errors


def check_already_passed(student, course, standing: AcademicStanding) -> list[str]:
    """درسی که قبلاً پاس شده دوباره قابل انتخاب نیست."""
    if course.id in standing.passed_course_ids:
        return [f'درس «{course.name}» را قبلاً با نمرهٔ قبولی گذرانده‌اید.']
    return []


def check_capacity(offering) -> list[str]:
    """ظرفیت کلاس."""
    if offering is None:
        return []
    if offering.is_full:
        return [f'ظرفیت کلاس «{offering.professor.get_full_name()}» تکمیل شده است.']
    return []


def check_time_conflict(student, semester, offering) -> list[str]:
    """تداخل ساعت با کلاس‌هایی که همین ترم برداشته."""
    from .models import Enrollment

    if offering is None:
        return []
    new_sessions = list(offering.sessions.all())
    if not new_sessions:
        return []

    current = (
        Enrollment.objects
        .filter(student=student, semester=semester)
        .exclude(status='dropped')
        .exclude(teaching_assignment__isnull=True)
        .select_related('teaching_assignment', 'course')
        .prefetch_related('teaching_assignment__sessions')
    )
    for en in current:
        if en.teaching_assignment_id == offering.id:
            continue
        for existing in en.teaching_assignment.sessions.all():
            for new in new_sessions:
                if new.overlaps(existing):
                    return [
                        f'تداخل ساعت با درس «{en.course.name}» در '
                        f'{existing.get_day_display()} '
                        f'{existing.start_time.strftime("%H:%M")}–'
                        f'{existing.end_time.strftime("%H:%M")}.'
                    ]
    return []


def check_unit_cap(course, current_units: int, standing: AcademicStanding) -> list[str]:
    """سقف واحد، با در نظر گرفتن مشروطی."""
    new_total = current_units + course.credits
    if new_total > standing.max_units:
        msg = f'سقف مجاز واحد ({standing.max_units}) رد می‌شود.'
        if standing.is_probation:
            msg += (
                f' معدل ترم گذشتهٔ شما {standing.last_semester_gpa} است و'
                f' مشروط محسوب می‌شوید.'
            )
        return [msg]
    return []


def can_enroll(student, course, semester, offering, current_units: int,
               standing: AcademicStanding | None = None) -> list[str]:
    """همهٔ قواعد یک‌جا. لیست خالی یعنی مجاز."""
    st = standing or get_standing(student, semester)
    errors = []
    errors += check_already_passed(student, course, st)
    errors += check_prerequisites(student, course, st)
    errors += check_corequisites(student, course, semester, st)
    errors += check_unit_cap(course, current_units, st)
    errors += check_capacity(offering)
    errors += check_time_conflict(student, semester, offering)
    return errors


def check_final_submission(student, semester, standing: AcademicStanding | None = None) -> list[str]:
    """بررسی حداقل واحد هنگام نهایی کردن انتخاب واحد."""
    from .models import Enrollment

    st = standing or get_standing(student, semester)
    units = sum(
        e.course.credits for e in
        Enrollment.objects.filter(student=student, semester=semester)
        .exclude(status='dropped').select_related('course')
    )
    if units == 0:
        return ['هیچ درسی انتخاب نکرده‌اید.']
    if units < st.min_units:
        # ترم آخر: اگر واحد باقیمانده کمتر از حد نصاب است، ایراد نگیر
        if _cfg('ALLOW_FINAL_TERM_UNDERLOAD', True) and st.total_required:
            if st.remaining_units and st.remaining_units <= st.min_units:
                return []
        return [
            f'حداقل واحد مجاز {st.min_units} است و شما {units} واحد انتخاب کرده‌اید.'
        ]
    return []
