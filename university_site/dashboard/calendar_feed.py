"""خروجی تقویم — کلاس‌ها و امتحانات به شکل یک فایل ics.

چرا
───
برنامهٔ هفتگی فقط قابل چاپ بود. دانشجو یا کاغذ را گم می‌کرد یا
هر بار وارد پنل می‌شد. یک فایل ics یعنی همان برنامه در تقویم گوشی،
با یادآور، بدون اینکه سامانه دسترسی به چیزی از او بخواهد.

کلاس‌ها رویداد هفتگی تکرارشونده‌اند تا پایان ترم؛ امتحان‌ها
رویداد یک‌باره.

بدون کتابخانه
─────────────
`icalendar` یک وابستگی تازه است برای ساختن متنی که خودش سی خط
است — و روی این هاست هر وابستگی تازه یعنی یک نصب دستی دیگر.

منطقهٔ زمانی
────────────
همه‌چیز به‌صورت زمان محلیِ بدون منطقه (floating) نوشته می‌شود.
موسسه و دانشجویانش هر دو در ایران‌اند، پس ساعت ۸ صبح در هر
دستگاهی ۸ صبح خوانده می‌شود — و این از نوشتن اشتباهِ منطقه امن‌تر
است.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

# روز هفتهٔ ایرانی (۰=شنبه) → کد تکرار در ics
ICS_DAYS = ['SA', 'SU', 'MO', 'TU', 'WE', 'TH', 'FR']

# فاصلهٔ روز شنبه تا دوشنبه‌ای که پایتون مبنا می‌گیرد
_PY_WEEKDAY_OF_SATURDAY = 5


def _escape(text: str) -> str:
    """کاراکترهای معنادار در ics باید backslash بگیرند."""
    return (
        str(text or '')
        .replace('\\', '\\\\')
        .replace(';', '\\;')
        .replace(',', '\\,')
        .replace('\n', '\\n')
    )


def _fold(line: str) -> str:
    """خطوط بلندتر از ۷۵ بایت باید شکسته شوند (RFC 5545).

    بعضی تقویم‌ها خط بلند را دور می‌ریزند و رویداد بی‌عنوان می‌شود.
    شکستن روی بایت انجام می‌شود نه روی نویسه، وگرنه یک حرف فارسی
    وسط دو خط نصف می‌شود.
    """
    raw = line.encode('utf-8')
    if len(raw) <= 73:
        return line
    parts, chunk = [], b''
    for char in line:
        piece = char.encode('utf-8')
        if len(chunk) + len(piece) > 73:
            parts.append(chunk.decode('utf-8'))
            chunk = b' '           # خط ادامه با یک فاصله شروع می‌شود
        chunk += piece
    parts.append(chunk.decode('utf-8'))
    return '\r\n'.join(parts)


def _stamp(value) -> str:
    if isinstance(value, datetime):
        return value.strftime('%Y%m%dT%H%M%S')
    return value.strftime('%Y%m%d')


def _first_occurrence(start: date, day: int) -> date:
    """اولین تاریخِ آن روز هفته، از شروع ترم به بعد.

    `day` با تقویم ایرانی می‌آید (۰=شنبه) و پایتون دوشنبه را ۰
    می‌گیرد؛ این تفاوت جای همیشگی خطاست.
    """
    target = (day + _PY_WEEKDAY_OF_SATURDAY) % 7
    delta = (target - start.weekday()) % 7
    return start + timedelta(days=delta)


def _event(uid, summary, start_dt, end_dt, location='', description='',
           until=None, byday='') -> list[str]:
    lines = [
        'BEGIN:VEVENT',
        'UID:%s' % uid,
        'DTSTAMP:%sZ' % datetime.utcnow().strftime('%Y%m%dT%H%M%S'),
        'DTSTART:%s' % _stamp(start_dt),
        'DTEND:%s' % _stamp(end_dt),
        'SUMMARY:%s' % _escape(summary),
    ]
    if byday and until:
        lines.append('RRULE:FREQ=WEEKLY;BYDAY=%s;UNTIL=%sT235959' % (byday, _stamp(until)))
    if location:
        lines.append('LOCATION:%s' % _escape(location))
    if description:
        lines.append('DESCRIPTION:%s' % _escape(description))
    # یادآور نیم‌ساعت قبل — همان چیزی که یک برنامهٔ چاپی نمی‌تواند بدهد
    lines += [
        'BEGIN:VALARM',
        'TRIGGER:-PT30M',
        'ACTION:DISPLAY',
        'DESCRIPTION:%s' % _escape(summary),
        'END:VALARM',
        'END:VEVENT',
    ]
    return [_fold(line) for line in lines]


def build(student, semester) -> str:
    """کل تقویم دانشجو برای یک ترم، به شکل متن ics."""
    from .models import Enrollment, ExamSchedule

    lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//AAB//Portal//FA',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
        _fold('X-WR-CALNAME:%s' % _escape(
            'برنامهٔ %s' % (semester.name if semester else 'ترم'))),
    ]

    enrollments = (
        Enrollment.objects
        .filter(student=student, status__in=['registered', 'in_progress'])
        .select_related('course', 'teaching_assignment')
    )
    if semester:
        enrollments = enrollments.filter(semester=semester)

    course_ids = []
    for enrollment in enrollments:
        course = enrollment.course
        if course:
            course_ids.append(course.id)
        offering = enrollment.teaching_assignment
        if not offering or not semester:
            continue
        for session in offering.sessions.all():
            first = _first_occurrence(semester.start_date, session.day)
            lines += _event(
                uid='class-%s-%s@portal.aab.ac.ir' % (offering.id, session.id),
                summary=course.name if course else 'کلاس',
                start_dt=datetime.combine(first, session.start_time),
                end_dt=datetime.combine(first, session.end_time),
                location=offering.classroom or '',
                description=(
                    'استاد: %s' % offering.professor.get_full_name()
                    if offering.professor_id else ''
                ),
                until=semester.end_date,
                byday=ICS_DAYS[session.day],
            )

    exams = ExamSchedule.objects.filter(course_id__in=course_ids).select_related('course')
    if semester:
        exams = exams.filter(semester=semester)
    for exam in exams:
        lines += _event(
            uid='exam-%s@portal.aab.ac.ir' % exam.id,
            summary='%s — %s' % (
                exam.get_exam_type_display(),
                exam.course.name if exam.course_id else '',
            ),
            start_dt=datetime.combine(exam.date, exam.start_time),
            end_dt=datetime.combine(exam.date, exam.end_time),
            location=exam.location or '',
            description=exam.instructions or '',
        )

    lines.append('END:VCALENDAR')
    # ics با CRLF بسته می‌شود؛ بعضی تقویم‌ها با \n خالی فایل را رد می‌کنند
    return '\r\n'.join(lines) + '\r\n'
