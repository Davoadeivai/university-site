"""تست‌های موتور قوانین انتخاب واحد.

اجرا:  python manage.py test dashboard
"""
from datetime import date, time, timedelta

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from academics.models import Course, Department, Major
from accounts.models import UserProfile
from dashboard.enrollment_rules import (
    can_enroll, check_final_submission, get_standing,
)
from dashboard.models import ClassSession, Enrollment, Semester, TeachingAssignment


def make_world():
    dep = Department.objects.create(name='فنی و مهندسی')
    major = Major.objects.create(
        name='مهندسی کامپیوتر', degree='bachelor_cont',
        department=dep, is_active=True, total_credits=140,
    )
    today = date.today()
    sem_prev = Semester.objects.create(
        name='ترم گذشته', semester_type='fall', academic_year='1403-1404',
        start_date=today - timedelta(days=300), end_date=today - timedelta(days=180),
    )
    sem = Semester.objects.create(
        name='ترم جاری', semester_type='spring', academic_year='1404-1405',
        start_date=today - timedelta(days=10), end_date=today + timedelta(days=100),
        is_active=True, registration_open=True,
    )
    prof = User.objects.create_user('prof1', password='x', first_name='رضا', last_name='کاظمی')
    student = User.objects.create_user('2000000001', password='x')
    UserProfile.objects.update_or_create(
        user=student, defaults={'role': 'student', 'major': major,
                                'national_id': '2000000001'},
    )
    return dep, major, sem_prev, sem, prof, student


def make_course(major, name, credits=3, code=''):
    return Course.objects.create(major=major, name=name, credits=credits, code=code)


def make_offering(prof, course, sem, capacity=0, sessions=()):
    ta = TeachingAssignment.objects.create(
        professor=prof, course=course, semester=sem, capacity=capacity,
    )
    for day, start, end in sessions:
        ClassSession.objects.create(
            teaching_assignment=ta, day=day, start_time=start, end_time=end,
        )
    return ta


@override_settings(SMS_ENABLED=False)
class PrerequisiteTests(TestCase):
    def setUp(self):
        _, self.major, self.sem_prev, self.sem, self.prof, self.student = make_world()
        self.basic = make_course(self.major, 'پایگاه داده')
        self.advanced = make_course(self.major, 'پایگاه داده پیشرفته')
        self.advanced.prereq_courses.add(self.basic)

    def test_blocked_without_prerequisite(self):
        st = get_standing(self.student, self.sem)
        errors = can_enroll(self.student, self.advanced, self.sem, None, 0, st)
        self.assertTrue(any('پیش‌نیاز' in e for e in errors), errors)

    def test_allowed_after_passing_prerequisite(self):
        Enrollment.objects.create(
            student=self.student, course=self.basic, semester=self.sem_prev,
            status='completed', final_grade=15,
        )
        st = get_standing(self.student, self.sem)
        errors = can_enroll(self.student, self.advanced, self.sem, None, 0, st)
        self.assertEqual(errors, [])

    def test_failing_grade_does_not_satisfy_prerequisite(self):
        Enrollment.objects.create(
            student=self.student, course=self.basic, semester=self.sem_prev,
            status='failed', final_grade=8,
        )
        st = get_standing(self.student, self.sem)
        errors = can_enroll(self.student, self.advanced, self.sem, None, 0, st)
        self.assertTrue(any('پیش‌نیاز' in e for e in errors), errors)


@override_settings(SMS_ENABLED=False)
class AlreadyPassedTests(TestCase):
    def setUp(self):
        _, self.major, self.sem_prev, self.sem, self.prof, self.student = make_world()
        self.course = make_course(self.major, 'ریاضی ۱')

    def test_cannot_retake_passed_course(self):
        Enrollment.objects.create(
            student=self.student, course=self.course, semester=self.sem_prev,
            status='completed', final_grade=18,
        )
        st = get_standing(self.student, self.sem)
        errors = can_enroll(self.student, self.course, self.sem, None, 0, st)
        self.assertTrue(any('گذرانده' in e for e in errors), errors)

    def test_can_retake_failed_course(self):
        Enrollment.objects.create(
            student=self.student, course=self.course, semester=self.sem_prev,
            status='failed', final_grade=7,
        )
        st = get_standing(self.student, self.sem)
        errors = can_enroll(self.student, self.course, self.sem, None, 0, st)
        self.assertEqual(errors, [])


@override_settings(SMS_ENABLED=False)
class CapacityTests(TestCase):
    def setUp(self):
        _, self.major, _, self.sem, self.prof, self.student = make_world()
        self.course = make_course(self.major, 'شبکه')
        self.offering = make_offering(self.prof, self.course, self.sem, capacity=1)

    def test_full_class_is_blocked(self):
        other = User.objects.create_user('2000000002', password='x')
        Enrollment.objects.create(
            student=other, course=self.course, semester=self.sem,
            teaching_assignment=self.offering, status='registered',
        )
        self.assertTrue(self.offering.is_full)
        errors = can_enroll(self.student, self.course, self.sem, self.offering, 0)
        self.assertTrue(any('ظرفیت' in e for e in errors), errors)

    def test_zero_capacity_means_unlimited(self):
        free = make_offering(self.prof, make_course(self.major, 'آزاد'), self.sem, capacity=0)
        self.assertIsNone(free.remaining_seats)
        self.assertFalse(free.is_full)

    def test_dropped_enrollment_frees_a_seat(self):
        other = User.objects.create_user('2000000003', password='x')
        en = Enrollment.objects.create(
            student=other, course=self.course, semester=self.sem,
            teaching_assignment=self.offering, status='registered',
        )
        self.assertTrue(self.offering.is_full)
        en.status = 'dropped'
        en.save()
        self.assertFalse(self.offering.is_full)


@override_settings(SMS_ENABLED=False)
class TimeConflictTests(TestCase):
    def setUp(self):
        _, self.major, _, self.sem, self.prof, self.student = make_world()
        self.c1 = make_course(self.major, 'درس اول')
        self.c2 = make_course(self.major, 'درس دوم')
        # هر دو شنبه ۱۰ تا ۱۲
        self.o1 = make_offering(self.prof, self.c1, self.sem,
                                sessions=[(0, time(10, 0), time(12, 0))])
        prof2 = User.objects.create_user('prof2', password='x', last_name='احمدی')
        self.o2 = make_offering(prof2, self.c2, self.sem,
                                sessions=[(0, time(11, 0), time(13, 0))])

    def test_overlapping_sessions_are_blocked(self):
        Enrollment.objects.create(
            student=self.student, course=self.c1, semester=self.sem,
            teaching_assignment=self.o1, status='registered',
        )
        errors = can_enroll(self.student, self.c2, self.sem, self.o2, 3)
        self.assertTrue(any('تداخل' in e for e in errors), errors)

    def test_different_day_is_allowed(self):
        Enrollment.objects.create(
            student=self.student, course=self.c1, semester=self.sem,
            teaching_assignment=self.o1, status='registered',
        )
        self.o2.sessions.all().update(day=2)  # دوشنبه
        errors = can_enroll(self.student, self.c2, self.sem, self.o2, 3)
        self.assertEqual(errors, [])

    def test_touching_but_not_overlapping_is_allowed(self):
        """کلاس ۱۰–۱۲ و ۱۲–۱۴ تداخل ندارند."""
        Enrollment.objects.create(
            student=self.student, course=self.c1, semester=self.sem,
            teaching_assignment=self.o1, status='registered',
        )
        self.o2.sessions.all().update(start_time=time(12, 0), end_time=time(14, 0))
        errors = can_enroll(self.student, self.c2, self.sem, self.o2, 3)
        self.assertEqual(errors, [])


@override_settings(SMS_ENABLED=False, MAX_REGISTRATION_UNITS=20,
                   PROBATION_MAX_UNITS=14, PROBATION_GPA=12)
class ProbationAndUnitCapTests(TestCase):
    def setUp(self):
        _, self.major, self.sem_prev, self.sem, self.prof, self.student = make_world()

    def _grade_last_semester(self, grade):
        c = make_course(self.major, f'درس {grade}', credits=3)
        Enrollment.objects.create(
            student=self.student, course=c, semester=self.sem_prev,
            status='completed', final_grade=grade,
        )

    def test_good_student_gets_full_cap(self):
        self._grade_last_semester(17)
        st = get_standing(self.student, self.sem)
        self.assertFalse(st.is_probation)
        self.assertEqual(st.max_units, 20)

    def test_probation_lowers_the_cap(self):
        self._grade_last_semester(9)
        st = get_standing(self.student, self.sem)
        self.assertTrue(st.is_probation)
        self.assertEqual(st.max_units, 14)

    def test_unit_cap_is_enforced(self):
        self._grade_last_semester(9)   # مشروط، سقف ۱۴
        course = make_course(self.major, 'درس جدید', credits=3)
        st = get_standing(self.student, self.sem)
        errors = can_enroll(self.student, course, self.sem, None, 12, st)
        self.assertTrue(any('سقف' in e for e in errors), errors)

    def test_min_units_enforced_on_submission(self):
        c = make_course(self.major, 'تک درس', credits=3)
        Enrollment.objects.create(
            student=self.student, course=c, semester=self.sem, status='registered',
        )
        issues = check_final_submission(self.student, self.sem)
        self.assertTrue(any('حداقل' in i for i in issues), issues)


@override_settings(SMS_ENABLED=False)
class StandingTests(TestCase):
    def setUp(self):
        _, self.major, self.sem_prev, self.sem, self.prof, self.student = make_world()

    def test_progress_counts_only_passed_units(self):
        passed = make_course(self.major, 'قبول', credits=4)
        failed = make_course(self.major, 'مردود', credits=3)
        Enrollment.objects.create(student=self.student, course=passed,
                                  semester=self.sem_prev, final_grade=16)
        Enrollment.objects.create(student=self.student, course=failed,
                                  semester=self.sem_prev, final_grade=6)
        st = get_standing(self.student, self.sem)
        self.assertEqual(st.passed_units, 4)
        self.assertEqual(st.total_required, 140)
        self.assertEqual(st.remaining_units, 136)

    def test_retake_uses_latest_grade(self):
        c = make_course(self.major, 'تکرار', credits=3)
        Enrollment.objects.create(student=self.student, course=c,
                                  semester=self.sem_prev, final_grade=8)
        Enrollment.objects.create(student=self.student, course=c,
                                  semester=self.sem, final_grade=17)
        st = get_standing(self.student, self.sem)
        self.assertEqual(st.passed_units, 3, 'نمرهٔ آخر باید ملاک باشد')


@override_settings(SMS_ENABLED=False)
class GradeRangeTests(TestCase):
    """اعتبارسنجی نمره باید سمت سرور باشد، نه فقط روی widget."""

    def setUp(self):
        _, self.major, _, self.sem, self.prof, self.student = make_world()
        self.course = make_course(self.major, 'درس')

    def test_out_of_range_grade_is_rejected(self):
        from django.core.exceptions import ValidationError
        en = Enrollment(student=self.student, course=self.course,
                        semester=self.sem, final_grade=99)
        with self.assertRaises(ValidationError):
            en.full_clean()

    def test_negative_grade_is_rejected(self):
        from django.core.exceptions import ValidationError
        en = Enrollment(student=self.student, course=self.course,
                        semester=self.sem, final_grade=-5)
        with self.assertRaises(ValidationError):
            en.full_clean()

    def test_valid_grade_passes(self):
        en = Enrollment(student=self.student, course=self.course,
                        semester=self.sem, final_grade=18.75)
        en.full_clean()  # نباید خطا بدهد
