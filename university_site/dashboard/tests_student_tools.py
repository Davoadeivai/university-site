"""تست‌های سه ابزار تازهٔ پنل دانشجو.

نوار کارهای فوری، راهنمای انتخاب واحد، و خروجی تقویم — هر سه روی
داده‌ای کار می‌کنند که از قبل در پایگاه داده هست، پس بیشترِ این
تست‌ها دربارهٔ «چه چیزی نباید نشان داده شود» است، نه «چه چیزی
نشان داده شود».
"""
from datetime import date, time, timedelta

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from dashboard.models import (
    Assignment, AssignmentSubmission, Enrollment, ExamSchedule, Payment,
)
from dashboard.tests import make_course, make_offering, make_world


@override_settings(SMS_ENABLED=False)
class TodayTasksTests(TestCase):
    """فقط چیزهای ضرب‌الاجل‌دارِ انجام‌نشده."""

    def setUp(self):
        _, self.major, _, self.sem, self.prof, self.student = make_world()
        self.course = make_course(self.major, 'ریاضی ۱')

    def _enroll(self):
        return Enrollment.objects.create(
            student=self.student, course=self.course, semester=self.sem,
            status='registered',
        )

    def test_empty_when_nothing_is_due(self):
        from dashboard import today
        self.assertEqual(today.build(self.student, [self.course.id]), [])

    def test_a_due_installment_shows_up(self):
        from dashboard import today
        Payment.objects.create(
            student=self.student, payment_type='tuition', amount=5000000,
            semester=self.sem, status='pending',
            due_date=date.today() + timedelta(days=3),
        )
        rows = today.build(self.student, [])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['kind'], 'payment')
        self.assertIn('روز مانده', rows[0]['when'])

    def test_a_paid_installment_does_not(self):
        from dashboard import today
        Payment.objects.create(
            student=self.student, payment_type='tuition', amount=5000000,
            semester=self.sem, status='paid',
            due_date=date.today() + timedelta(days=3),
        )
        self.assertEqual(today.build(self.student, []), [])

    def test_a_far_off_installment_does_not(self):
        from dashboard import today
        Payment.objects.create(
            student=self.student, payment_type='tuition', amount=1000,
            semester=self.sem, status='pending',
            due_date=date.today() + timedelta(days=60),
        )
        self.assertEqual(today.build(self.student, []), [])

    def test_a_handed_in_assignment_does_not(self):
        from dashboard import today
        self._enroll()
        homework = Assignment.objects.create(
            course=self.course, semester=self.sem, professor=self.prof,
            title='سری ۱', description='—', assignment_type='homework',
            due_date=timezone.now() + timedelta(days=2),
        )
        self.assertEqual(len(today.build(self.student, [self.course.id])), 1)
        AssignmentSubmission.objects.create(
            assignment=homework, student=self.student, status='submitted')
        self.assertEqual(today.build(self.student, [self.course.id]), [])

    def test_at_most_three_rows(self):
        from dashboard import today
        for offset in range(6):
            Payment.objects.create(
                student=self.student, payment_type='tuition', amount=1000,
                semester=self.sem, status='pending',
                due_date=date.today() + timedelta(days=offset),
            )
        self.assertLessEqual(len(today.build(self.student, [])), 3)

    def test_the_nearest_deadline_comes_first(self):
        from dashboard import today
        self._enroll()
        Payment.objects.create(
            student=self.student, payment_type='tuition', amount=1000,
            semester=self.sem, status='pending',
            due_date=date.today() + timedelta(days=8),
        )
        Assignment.objects.create(
            course=self.course, semester=self.sem, professor=self.prof,
            title='فردا', description='—', assignment_type='homework',
            due_date=timezone.now() + timedelta(days=1),
        )
        rows = today.build(self.student, [self.course.id])
        self.assertEqual(rows[0]['kind'], 'assignment')


@override_settings(SMS_ENABLED=False)
class AdvisorTests(TestCase):
    """ترم دانشجو از روی درس‌های پاس‌شده، نه از روی تاریخ ثبت‌نام."""

    def setUp(self):
        _, self.major, self.sem_prev, self.sem, self.prof, self.student = make_world()

    def _course(self, name, term):
        course = make_course(self.major, name)
        course.semester = term
        course.save(update_fields=['semester'])
        return course

    def _pass(self, course, grade=15):
        Enrollment.objects.create(
            student=self.student, course=course, semester=self.sem_prev,
            status='completed', final_grade=grade,
        )

    def test_a_fresh_student_is_in_term_one(self):
        from dashboard import advisor
        self.assertEqual(advisor.current_term(self.student, self.major), 1)

    def test_term_follows_the_highest_passed_course(self):
        from dashboard import advisor
        self._pass(self._course('ریاضی ۱', 1))
        self._pass(self._course('فیزیک', 2))
        self.assertEqual(advisor.current_term(self.student, self.major), 3)

    def test_a_failed_course_does_not_advance_the_term(self):
        from dashboard import advisor
        self._pass(self._course('ریاضی ۱', 1))
        self._pass(self._course('فیزیک', 2), grade=8)
        self.assertEqual(advisor.current_term(self.student, self.major), 2)

    def test_grouping_splits_by_term_and_blockers(self):
        from dashboard import advisor
        mine = self._course('درس ترم ۱', 1)
        later = self._course('درس ترم ۵', 5)
        blocked = self._course('قفل', 1)
        rows = [
            {'course': mine, 'enrolled': False, 'blocked': False},
            {'course': later, 'enrolled': False, 'blocked': False},
            {'course': blocked, 'enrolled': False, 'blocked': True},
        ]
        groups = advisor.group_rows(rows, term=1)
        self.assertEqual([r['course'] for r in groups['suggested']], [mine])
        self.assertEqual([r['course'] for r in groups['available']], [later])
        self.assertEqual([r['course'] for r in groups['later']], [blocked])

    def test_enrolled_rows_are_left_out(self):
        from dashboard import advisor
        course = self._course('گرفته‌شده', 1)
        groups = advisor.group_rows(
            [{'course': course, 'enrolled': True, 'blocked': False}], term=1)
        self.assertEqual(groups['suggested'], [])
        self.assertEqual(groups['available'], [])
        self.assertEqual(groups['later'], [])

    def test_suggested_units_are_summed(self):
        from dashboard import advisor
        first = self._course('الف', 1)
        second = self._course('ب', 1)
        rows = [
            {'course': first, 'enrolled': False, 'blocked': False},
            {'course': second, 'enrolled': False, 'blocked': False},
        ]
        advice = advisor.build(self.student, self.major, rows)
        self.assertEqual(advice['term'], 1)
        self.assertEqual(advice['suggested_units'],
                         first.credits + second.credits)


@override_settings(SMS_ENABLED=False)
class CalendarFeedTests(TestCase):
    """فایل ics باید ساختار درست و رویدادهای واقعی داشته باشد."""

    def setUp(self):
        _, self.major, _, self.sem, self.prof, self.student = make_world()
        self.course = make_course(self.major, 'شبکه')
        self.offering = make_offering(
            self.prof, self.course, self.sem,
            sessions=[(0, time(8, 0), time(10, 0))],
        )
        Enrollment.objects.create(
            student=self.student, course=self.course, semester=self.sem,
            status='registered', teaching_assignment=self.offering,
        )

    def test_it_is_a_well_formed_calendar(self):
        from dashboard import calendar_feed
        body = calendar_feed.build(self.student, self.sem)
        self.assertTrue(body.startswith('BEGIN:VCALENDAR'))
        self.assertTrue(body.rstrip().endswith('END:VCALENDAR'))
        self.assertIn('\r\n', body)

    def test_a_weekly_class_repeats_until_the_term_ends(self):
        from dashboard import calendar_feed
        body = calendar_feed.build(self.student, self.sem)
        self.assertIn('FREQ=WEEKLY', body)
        self.assertIn('BYDAY=SA', body)
        self.assertIn(self.sem.end_date.strftime('%Y%m%d'), body)

    def test_the_first_class_lands_on_a_saturday(self):
        from dashboard.calendar_feed import _first_occurrence
        start = date(2026, 8, 19)              # چهارشنبه
        first = _first_occurrence(start, 0)    # ۰ = شنبه در تقویم ایرانی
        self.assertEqual(first.weekday(), 5)   # پایتون: ۵ = شنبه
        self.assertGreaterEqual(first, start)

    def test_an_exam_becomes_a_one_off_event(self):
        from dashboard import calendar_feed
        ExamSchedule.objects.create(
            course=self.course, semester=self.sem, exam_type='final',
            date=date.today() + timedelta(days=30),
            start_time=time(9, 0), end_time=time(11, 0), location='سالن ۱',
        )
        body = calendar_feed.build(self.student, self.sem)
        self.assertIn('پایان‌ترم', body)
        self.assertIn('سالن ۱', body)

    def test_long_lines_are_folded(self):
        from dashboard.calendar_feed import _fold
        folded = _fold('SUMMARY:' + 'درس بسیار طولانی ' * 12)
        for line in folded.split('\r\n'):
            self.assertLessEqual(len(line.encode('utf-8')), 75)

    def test_every_event_carries_a_reminder(self):
        from dashboard import calendar_feed
        body = calendar_feed.build(self.student, self.sem)
        self.assertEqual(body.count('BEGIN:VEVENT'), body.count('BEGIN:VALARM'))

    def test_the_view_serves_a_calendar_file(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse('dashboard:student_calendar_ics'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/calendar', response['Content-Type'])
        self.assertIn('.ics', response['Content-Disposition'])
