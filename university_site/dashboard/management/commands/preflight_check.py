"""بررسی پیش‌از‌دیپلوی: آیا داده‌های فعلی محدودیت‌های جدید را نقض می‌کنند؟

سه محدودیت جدید در این نسخه اضافه شده و اگر داده‌ی موجود نقضشان کند،
`migrate` روی سرور شکست می‌خورد و نیمه‌کاره می‌ماند:

  1. uniq_active_application_per_national_id  (admissions.Application)
  2. uniq_profile_national_id                 (accounts.UserProfile)
  3. enrollment_final_grade_range / midterm   (dashboard.Enrollment)

این دستور را **پیش از** migrate روی سرور اجرا کنید:
    python manage.py preflight_check
"""
from collections import Counter

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'بررسی نقض محدودیت‌های جدید پیش از اجرای migrate روی سرور'

    def handle(self, *args, **options):
        from accounts.models import UserProfile
        from admissions.models import Application
        from dashboard.models import Enrollment

        problems = 0

        # ── ۱) کد ملی تکراری در درخواست‌های فعال ──
        self.stdout.write(self.style.MIGRATE_HEADING(
            '\n[۱] کد ملی تکراری در درخواست‌های پذیرش فعال'))
        rows = (
            Application.objects
            .exclude(status='rejected').exclude(national_id='')
            .values_list('id', 'national_id', 'tracking_code', 'status')
        )
        counts = Counter(r[1] for r in rows)
        dupes = {nid: n for nid, n in counts.items() if n > 1}
        if dupes:
            problems += 1
            self.stdout.write(self.style.ERROR(
                f'  ✗ {len(dupes)} کد ملی تکراری پیدا شد — migrate شکست می‌خورد:'))
            for nid in dupes:
                for r in rows:
                    if r[1] == nid:
                        self.stdout.write(
                            f'      pk={r[0]}  کد ملی={nid}  رهگیری={r[2]}  وضعیت={r[3]}')
            self.stdout.write(self.style.WARNING(
                '    راه‌حل: یکی از هر جفت را به وضعیت «رد شده» تغییر دهید یا حذف کنید.'))
        else:
            self.stdout.write(self.style.SUCCESS('  ✓ تکراری نیست'))

        # ── ۲) کد ملی تکراری در پروفایل‌ها ──
        self.stdout.write(self.style.MIGRATE_HEADING(
            '\n[۲] کد ملی تکراری در پروفایل کاربران'))
        prows = (
            UserProfile.objects.exclude(national_id='')
            .values_list('id', 'national_id', 'user__username')
        )
        pcounts = Counter(r[1] for r in prows)
        pdupes = {nid: n for nid, n in pcounts.items() if n > 1}
        if pdupes:
            problems += 1
            self.stdout.write(self.style.ERROR(
                f'  ✗ {len(pdupes)} کد ملی تکراری — migrate شکست می‌خورد:'))
            for nid in pdupes:
                for r in prows:
                    if r[1] == nid:
                        self.stdout.write(
                            f'      profile pk={r[0]}  کد ملی={nid}  کاربر={r[2]}')
            self.stdout.write(self.style.WARNING(
                '    راه‌حل: کد ملی یکی از حساب‌ها را اصلاح یا خالی کنید.'))
        else:
            self.stdout.write(self.style.SUCCESS('  ✓ تکراری نیست'))

        # ── ۳) نمره خارج از بازه ۰ تا ۲۰ ──
        self.stdout.write(self.style.MIGRATE_HEADING(
            '\n[۳] نمره خارج از بازه ۰ تا ۲۰'))
        bad = []
        for field in ('final_grade', 'mid_term_grade', 'attendance_score'):
            qs = Enrollment.objects.exclude(**{f'{field}__isnull': True}).exclude(
                **{f'{field}__gte': 0, f'{field}__lte': 20})
            for en in qs.select_related('student', 'course'):
                bad.append((field, en))
        if bad:
            problems += 1
            self.stdout.write(self.style.ERROR(
                f'  ✗ {len(bad)} نمره نامعتبر — migrate شکست می‌خورد:'))
            for field, en in bad:
                self.stdout.write(
                    f'      enrollment pk={en.pk}  {field}={getattr(en, field)}  '
                    f'دانشجو={en.student.username}  درس={en.course.name}')
            self.stdout.write(self.style.WARNING(
                '    راه‌حل: نمره را اصلاح یا خالی کنید.'))
        else:
            self.stdout.write(self.style.SUCCESS('  ✓ همه نمرات در بازه مجاز'))

        # ── هشدارهای غیربحرانی ──
        self.stdout.write(self.style.MIGRATE_HEADING('\n[۴] هشدارها (مانع migrate نیستند)'))
        from dashboard.models import ClassSession, TeachingAssignment
        ta_total = TeachingAssignment.objects.count()
        ta_no_session = TeachingAssignment.objects.filter(sessions__isnull=True).count()
        if ta_no_session:
            self.stdout.write(self.style.WARNING(
                f'  ! {ta_no_session} از {ta_total} کلاس هیچ «جلسه هفتگی» ندارد؛'
                ' تشخیص تداخل ساعت برایشان کار نمی‌کند.'))
            self.stdout.write(
                '    از پنل: تخصیص‌های تدریس ← هر کلاس ← جلسات هفتگی')
        else:
            self.stdout.write(self.style.SUCCESS('  ✓ همه کلاس‌ها جلسه دارند'))

        no_cap = TeachingAssignment.objects.filter(capacity=0).count()
        if no_cap:
            self.stdout.write(self.style.WARNING(
                f'  ! {no_cap} کلاس ظرفیت نامحدود دارند (capacity=0).'))

        supers = list(
            __import__('django.contrib.auth.models', fromlist=['User'])
            .User.objects.filter(is_superuser=True)
            .values_list('username', flat=True)
        )
        self.stdout.write(f'  · ابرکاربران فعلی: {", ".join(supers) or "هیچ"}')

        # ── نتیجه ──
        self.stdout.write('')
        if problems:
            self.stdout.write(self.style.ERROR(
                f'✗ {problems} مورد بحرانی. پیش از migrate اصلاحشان کنید.'))
            raise SystemExit(1)
        self.stdout.write(self.style.SUCCESS(
            '✓ داده‌ها آمادهٔ migrate هستند.'))
