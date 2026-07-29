from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from academics.models import Major, Course, Department


class Semester(models.Model):
    SEMESTER_CHOICES = [
        ('fall', 'پاییز'),
        ('spring', 'بهار'),
        ('summer', 'تابستان'),
    ]
    name = models.CharField(_('نام ترم'), max_length=100)
    semester_type = models.CharField(_('نوع ترم'), max_length=20, choices=SEMESTER_CHOICES)
    academic_year = models.CharField(_('سال تحصیلی'), max_length=20)
    start_date = models.DateField(_('تاریخ شروع'))
    end_date = models.DateField(_('تاریخ پایان'))
    is_active = models.BooleanField(_('فعال'), default=False)
    registration_open = models.BooleanField(_('ثبت‌نام باز'), default=False)

    class Meta:
        verbose_name = _('ترم')
        verbose_name_plural = _('ترم‌ها')
        ordering = ['-academic_year', '-start_date']

    def __str__(self):
        return f"{self.name} - {self.academic_year}"

    def clean(self):
        """#11 + #20: جلوگیری از دو ترم is_active=True همزمان."""
        from django.core.exceptions import ValidationError
        if self.is_active:
            conflict = Semester.objects.filter(is_active=True).exclude(pk=self.pk)
            if conflict.exists():
                names = ', '.join(conflict.values_list('name', flat=True))
                raise ValidationError(
                    f'ترم فعال دیگری وجود دارد: {names}. '
                    'ابتدا آن را غیرفعال کنید.'
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Enrollment(models.Model):
    STATUS_CHOICES = [
        ('registered', 'ثبت‌نام شده'),
        ('in_progress', 'در حال گذراندن'),
        ('completed', 'تکمیل شده'),
        ('dropped', 'حذف شده'),
        ('failed', 'مردود'),
    ]
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments', verbose_name=_('دانشجو'))
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments', verbose_name=_('درس'))
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name='enrollments', verbose_name=_('ترم'))
    teaching_assignment = models.ForeignKey(
        'TeachingAssignment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='enrollments',
        verbose_name=_('کلاس / استاد انتخابی'),
    )
    status = models.CharField(_('وضعیت'), max_length=20, choices=STATUS_CHOICES, default='registered')
    # اعتبارسنجی سمت سرور — پیش از این فقط min/max روی widget بود و با
    # یک POST مستقیم می‌شد نمرهٔ ۹۹ یا منفی ثبت کرد.
    mid_term_grade = models.DecimalField(
        _('نمره میان‌ترم'), max_digits=5, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(20)],
    )
    final_grade = models.DecimalField(
        _('نمره نهایی'), max_digits=5, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(20)],
    )
    attendance_score = models.DecimalField(
        _('نمره حضور'), max_digits=5, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(20)],
    )
    retake_of = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='retakes', verbose_name=_('تکرار درسِ'),
    )
    exam_seat_no = models.CharField(_('شماره صندلی امتحان'), max_length=10, blank=True, default='')
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('ثبت‌نام درس')
        verbose_name_plural = _('ثبت‌نام دروس')
        unique_together = ['student', 'course', 'semester']
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(final_grade__isnull=True)
                    | models.Q(final_grade__gte=0, final_grade__lte=20)
                ),
                name='enrollment_final_grade_range',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(mid_term_grade__isnull=True)
                    | models.Q(mid_term_grade__gte=0, mid_term_grade__lte=20)
                ),
                name='enrollment_midterm_grade_range',
            ),
        ]

    @property
    def is_passed(self) -> bool:
        from django.conf import settings
        pass_mark = getattr(settings, 'PASSING_GRADE', 10)
        return self.final_grade is not None and float(self.final_grade) >= pass_mark

    def __str__(self):
        return f"{self.student.get_full_name()} - {self.course.name}"


class TeachingAssignment(models.Model):
    professor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='teaching_assignments', verbose_name=_('استاد'))
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='teaching_assignments', verbose_name=_('درس'))
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name='teaching_assignments', verbose_name=_('ترم'))
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('دانشکده'))
    # متن نمایشی. برنامهٔ واقعی برای تشخیص تداخل در ClassSession است.
    class_schedule = models.TextField(_('برنامه کلاس (متن)'), blank=True)
    classroom = models.CharField(_('کلاس'), max_length=50, blank=True)
    capacity = models.PositiveIntegerField(
        _('ظرفیت کلاس'), default=0,
        help_text=_('۰ یعنی بدون محدودیت. با پر شدن ظرفیت، انتخاب واحد بسته می‌شود.'),
    )
    is_active = models.BooleanField(_('فعال'), default=True)

    class Meta:
        verbose_name = _('تخصیص تدریس')
        verbose_name_plural = _('تخصیص‌های تدریس')
        unique_together = ['professor', 'course', 'semester']

    def __str__(self):
        return f"{self.professor.get_full_name()} - {self.course.name}"

    @property
    def taken_seats(self) -> int:
        return self.enrollments.exclude(status='dropped').count()

    @property
    def remaining_seats(self):
        """None یعنی بدون محدودیت."""
        if not self.capacity:
            return None
        return max(0, self.capacity - self.taken_seats)

    @property
    def is_full(self) -> bool:
        rem = self.remaining_seats
        return rem is not None and rem <= 0

    def schedule_display(self) -> str:
        sessions = list(self.sessions.all())
        if sessions:
            return '، '.join(str(s) for s in sessions)
        return self.class_schedule or '—'


class ClassSession(models.Model):
    """یک جلسهٔ هفتگی از یک کلاس.

    تا پیش از این برنامهٔ کلاس یک متن آزاد بود («شنبه و دوشنبه ۱۰–۱۲») و
    تداخل ساعت به‌هیچ‌وجه قابل تشخیص نبود. با این مدل، هر جلسه روز و ساعت
    مشخص دارد و موتور انتخاب واحد می‌تواند تداخل را ببیند.
    """
    DAY_CHOICES = [
        (0, 'شنبه'), (1, 'یکشنبه'), (2, 'دوشنبه'), (3, 'سه‌شنبه'),
        (4, 'چهارشنبه'), (5, 'پنجشنبه'), (6, 'جمعه'),
    ]

    teaching_assignment = models.ForeignKey(
        TeachingAssignment, on_delete=models.CASCADE,
        related_name='sessions', verbose_name=_('کلاس'),
    )
    day = models.PositiveSmallIntegerField(_('روز'), choices=DAY_CHOICES)
    start_time = models.TimeField(_('ساعت شروع'))
    end_time = models.TimeField(_('ساعت پایان'))

    class Meta:
        verbose_name = _('جلسه کلاس')
        verbose_name_plural = _('جلسات کلاس')
        ordering = ['day', 'start_time']
        unique_together = ['teaching_assignment', 'day', 'start_time']

    def __str__(self):
        return (
            f"{self.get_day_display()} "
            f"{self.start_time.strftime('%H:%M')}–{self.end_time.strftime('%H:%M')}"
        )

    def overlaps(self, other: 'ClassSession') -> bool:
        if self.day != other.day:
            return False
        return self.start_time < other.end_time and other.start_time < self.end_time


class StudentRequest(models.Model):
    REQUEST_TYPE_CHOICES = [
        ('certificate', 'گواهی'),
        ('transcript', 'کارنامه'),
        ('recommendation', 'معرفی‌نامه'),
        ('leave', 'مرخصی'),
        ('extension', 'تمدید'),
        ('complaint', 'شکایت'),
        ('other', 'سایر'),
    ]
    STATUS_CHOICES = [
        ('pending', 'در انتظار'),
        ('approved', 'تایید شده'),
        ('rejected', 'رد شده'),
        ('processing', 'در حال بررسی'),
    ]
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='requests', verbose_name=_('دانشجو'))
    request_type = models.CharField(_('نوع درخواست'), max_length=20, choices=REQUEST_TYPE_CHOICES)
    title = models.CharField(_('عنوان'), max_length=200)
    description = models.TextField(_('توضیحات'))
    status = models.CharField(_('وضعیت'), max_length=20, choices=STATUS_CHOICES, default='pending')
    response = models.TextField(_('پاسخ'), blank=True)
    file = models.FileField(_('فایل'), upload_to='requests/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('درخواست دانشجویی')
        verbose_name_plural = _('درخواست‌های دانشجویی')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.get_full_name()} - {self.title}"


class Payment(models.Model):
    """پرداخت‌های سامانه آموزشی (دانشجوی ثبت‌نام‌شده) — جدا از اقساط پذیرش."""
    PAYMENT_TYPE_CHOICES = [
        ('tuition', 'شهریه'),
        ('dorm', 'خوابگاه'),
        ('book', 'کتاب'),
        ('exam', 'امتحان'),
        ('other', 'سایر'),
    ]
    STATUS_CHOICES = [
        ('pending', 'در انتظار پرداخت'),
        ('review', 'در انتظار تأیید امور مالی'),
        ('paid', 'پرداخت شده'),
        ('failed', 'ناموفق'),
        ('refunded', 'بازگشت داده شده'),
    ]
    STAGE_CHOICES = [
        ('', '—'),
        ('initial', 'قسط اول (ثبت‌نام)'),
        ('mid', 'قسط دوم (میانی)'),
        ('exam_card', 'قسط سوم (کارت ورود به جلسه)'),
    ]
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments', verbose_name=_('دانشجو'))
    payment_type = models.CharField(_('نوع پرداخت'), max_length=20, choices=PAYMENT_TYPE_CHOICES)
    amount = models.PositiveIntegerField(_('مبلغ (تومان)'))
    semester = models.ForeignKey(Semester, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('ترم'))
    description = models.TextField(_('توضیحات'), blank=True)
    status = models.CharField(_('وضعیت'), max_length=20, choices=STATUS_CHOICES, default='pending')
    installment_no = models.PositiveSmallIntegerField(_('شماره قسط'), default=0, db_index=True)
    installment_stage = models.CharField(
        _('مرحله قسط'), max_length=20, choices=STAGE_CHOICES, blank=True, default='',
    )
    METHOD_CHOICES = [
        ('online', 'پرداخت آنلاین (درگاه)'),
        ('card_to_card', 'کارت‌به‌کارت'),
        ('pos', 'کارت‌خوان / کارتخوان در مؤسسه'),
        ('bank_deposit', 'فیش بانکی / واریز به حساب'),
        ('cash', 'نقدی در امور مالی'),
        ('other', 'سایر'),
    ]
    method = models.CharField(
        _('روش پرداخت'), max_length=20, choices=METHOD_CHOICES, default='online', blank=True,
    )
    due_date = models.DateField(_('سررسید قسط'), null=True, blank=True, db_index=True)
    receipt_file = models.FileField(
        _('فیش / رسید آفلاین'), upload_to='tuition_receipts/', blank=True, null=True,
    )
    receipt_ref = models.CharField(_('شماره پیگیری / مرجع'), max_length=100, blank=True)
    method_notes = models.TextField(_('توضیح روش پرداخت'), blank=True)
    reminder_sent_at = models.DateTimeField(_('آخرین یادآوری پیامکی'), null=True, blank=True)
    exam_barcode = models.CharField(_('بارکد کارت امتحان'), max_length=64, blank=True, db_index=True)
    transaction_id = models.CharField(_('شناسه تراکنش'), max_length=100, blank=True)
    authority = models.CharField(_('کد authority درگاه'), max_length=100, blank=True, db_index=True)
    gateway = models.CharField(_('درگاه'), max_length=20, blank=True, default='')
    payment_date = models.DateTimeField(_('تاریخ پرداخت'), null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('پرداخت سامانه آموزشی')
        verbose_name_plural = _('پرداخت‌های سامانه آموزشی')
        ordering = ['installment_no', '-created_at']

    def __str__(self):
        stage = self.get_installment_stage_display() if self.installment_stage else ''
        base = f"{self.student.get_full_name()} - {self.amount:,} تومان"
        return f"{base} ({stage})" if stage else base

    @property
    def is_exam_gate(self) -> bool:
        return self.installment_stage == 'exam_card'


class ExamSchedule(models.Model):
    EXAM_TYPE_CHOICES = [
        ('midterm', 'میان‌ترم'),
        ('final', 'پایان‌ترم'),
        ('makeup', 'امتحان جایگزین'),
        ('practical', 'امتحان عملی'),
    ]
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='exams', verbose_name=_('درس'))
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name='exams', verbose_name=_('ترم'))
    exam_type = models.CharField(_('نوع امتحان'), max_length=20, choices=EXAM_TYPE_CHOICES)
    date = models.DateField(_('تاریخ'))
    start_time = models.TimeField(_('ساعت شروع'))
    end_time = models.TimeField(_('ساعت پایان'))
    location = models.CharField(_('مکان'), max_length=100)
    instructions = models.TextField(_('دستورالعمل'), blank=True)

    class Meta:
        verbose_name = _('برنامه امتحان')
        verbose_name_plural = _('برنامه امتحانات')
        ordering = ['date', 'start_time']

    def __str__(self):
        return f"{self.course.name} - {self.get_exam_type_display()}"


class Assignment(models.Model):
    ASSIGNMENT_TYPE_CHOICES = [
        ('homework', 'تکلیف'),
        ('project', 'پروژه'),
        ('quiz', 'کوییز'),
        ('presentation', 'ارائه'),
    ]
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='assignments', verbose_name=_('درس'))
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name='assignments', verbose_name=_('ترم'))
    professor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assignments', verbose_name=_('استاد'))
    title = models.CharField(_('عنوان'), max_length=200)
    description = models.TextField(_('توضیحات'))
    assignment_type = models.CharField(_('نوع'), max_length=20, choices=ASSIGNMENT_TYPE_CHOICES)
    due_date = models.DateTimeField(_('مهلت تحویل'))
    max_score = models.PositiveIntegerField(_('امتیاز کل'), default=100)
    file = models.FileField(_('فایل'), upload_to='assignments/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(_('فعال'), default=True)

    class Meta:
        verbose_name = _('تکلیف')
        verbose_name_plural = _('تکالیف')
        ordering = ['-due_date']

    def __str__(self):
        return f"{self.course.name} - {self.title}"


class AssignmentSubmission(models.Model):
    STATUS_CHOICES = [
        ('submitted', 'تحویل داده شده'),
        ('graded', 'نمره داده شده'),
        ('late', 'تاخیری'),
        ('rejected', 'رد شده'),
    ]
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions', verbose_name=_('تکلیف'))
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submissions', verbose_name=_('دانشجو'))
    file = models.FileField(_('فایل'), upload_to='submissions/')
    submitted_at = models.DateTimeField(auto_now_add=True)
    grade = models.DecimalField(_('نمره'), max_digits=5, decimal_places=2, null=True, blank=True)
    feedback = models.TextField(_('بازخورد'), blank=True)
    status = models.CharField(_('وضعیت'), max_length=20, choices=STATUS_CHOICES, default='submitted')

    class Meta:
        verbose_name = _('تحویل تکلیف')
        verbose_name_plural = _('تحویل تکالیف')
        unique_together = ['assignment', 'student']

    def __str__(self):
        return f"{self.student.get_full_name()} - {self.assignment.title}"


class Attendance(models.Model):
    STATUS_CHOICES = [
        ('present', 'حاضر'),
        ('absent', 'غایب'),
        ('late', 'تاخیر'),
        ('excused', 'مرخصی'),
    ]
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name='attendance', verbose_name=_('ثبت‌نام'))
    date = models.DateField(_('تاریخ'))
    status = models.CharField(_('وضعیت'), max_length=20, choices=STATUS_CHOICES, default='present')
    notes = models.TextField(_('یادداشت'), blank=True)

    class Meta:
        verbose_name = _('حضور و غیاب')
        verbose_name_plural = _('حضور و غیاب')
        unique_together = ['enrollment', 'date']

    def __str__(self):
        return f"{self.enrollment.student.get_full_name()} - {self.date}"


class TuitionInstallmentPlan(models.Model):
    """نسبت و سررسید اقساط شهریه به‌ازای سال تحصیلی (ادمین)."""
    academic_year = models.CharField(_('سال تحصیلی'), max_length=20, unique=True)
    ratio_initial = models.PositiveSmallIntegerField(_('درصد قسط ۱'), default=40)
    ratio_mid = models.PositiveSmallIntegerField(_('درصد قسط ۲'), default=30)
    ratio_exam = models.PositiveSmallIntegerField(_('درصد قسط ۳'), default=30)
    due_days_initial = models.PositiveSmallIntegerField(_('سررسید قسط ۱ (روز از شروع ترم)'), default=7)
    due_days_mid = models.PositiveSmallIntegerField(_('سررسید قسط ۲ (روز از شروع ترم)'), default=60)
    due_days_exam = models.PositiveSmallIntegerField(_('سررسید قسط ۳ (روز از شروع ترم)'), default=100)
    reminder_days_before = models.PositiveSmallIntegerField(_('یادآوری پیامک چند روز قبل'), default=3)
    is_active = models.BooleanField(_('فعال'), default=True)
    notes = models.TextField(_('توضیحات'), blank=True)

    class Meta:
        verbose_name = _('برنامه اقساط شهریه')
        verbose_name_plural = _('برنامه‌های اقساط شهریه')
        ordering = ['-academic_year']

    def __str__(self):
        return f'{self.academic_year} ({self.ratio_initial}/{self.ratio_mid}/{self.ratio_exam})'

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.ratio_initial + self.ratio_mid + self.ratio_exam != 100:
            raise ValidationError('جمع درصد اقساط باید دقیقاً ۱۰۰ باشد.')

    @property
    def ratios(self):
        return (self.ratio_initial, self.ratio_mid, self.ratio_exam)


class StudentDiscountClaim(models.Model):
    """درخواست/اعمال تخفیف شهریه برای دانشجو (خواهر/برادر، ایثارگری، …)."""
    DISCOUNT_CHOICES = [
        ('sibling', 'تخفیف خواهر / برادر'),
        ('martyr', 'ایثارگری / خانواده شهید'),
        ('veteran', 'جانبازی / ایثارگری'),
        ('talent', 'استعداد درخشان'),
        ('other', 'سایر'),
    ]
    STATUS_CHOICES = [
        ('pending', 'در انتظار بررسی'),
        ('approved', 'تأیید شده'),
        ('rejected', 'رد شده'),
    ]
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='discount_claims', verbose_name=_('دانشجو'))
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name='discount_claims', verbose_name=_('ترم'))
    discount_type = models.CharField(_('نوع تخفیف'), max_length=20, choices=DISCOUNT_CHOICES)
    percent = models.PositiveSmallIntegerField(_('درصد تخفیف'), default=10)
    document = models.FileField(_('مدرک پیوست'), upload_to='tuition_discounts/', blank=True, null=True)
    notes = models.TextField(_('توضیحات دانشجو'), blank=True)
    status = models.CharField(_('وضعیت'), max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_note = models.TextField(_('یادداشت ادمین'), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _('تخفیف شهریه دانشجو')
        verbose_name_plural = _('تخفیف‌های شهریه دانشجو')
        ordering = ['-created_at']
        unique_together = ['student', 'semester', 'discount_type']

    def __str__(self):
        return f'{self.student} — {self.get_discount_type_display()} ({self.percent}%)'


class StudentClearance(models.Model):
    """تسویه پایان‌تحصیل / انصراف."""
    STATUS_CHOICES = [
        ('open', 'باز'),
        ('in_progress', 'در حال انجام'),
        ('completed', 'تکمیل‌شده'),
    ]
    student = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='clearance', verbose_name=_('دانشجو'),
    )
    status = models.CharField(_('وضعیت کل'), max_length=20, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(_('زمان تکمیل'), blank=True, null=True)

    class Meta:
        verbose_name = _('تسویه پایان‌تحصیل')
        verbose_name_plural = _('تسویه‌های پایان‌تحصیل')

    def __str__(self):
        return f'تسویه {self.student.get_full_name() or self.student.username}'

    def refresh_status(self, save=True):
        items = list(self.items.all())
        if not items:
            new_status = 'open'
        elif all(i.status in ('cleared', 'waived') for i in items):
            new_status = 'completed'
        elif any(i.status in ('cleared', 'waived') for i in items):
            new_status = 'in_progress'
        else:
            new_status = 'open'
        self.status = new_status
        if new_status == 'completed' and not self.completed_at:
            from django.utils import timezone
            self.completed_at = timezone.now()
        elif new_status != 'completed':
            self.completed_at = None
        if save:
            self.save(update_fields=['status', 'completed_at', 'updated_at'])
        return self.status

    @property
    def is_complete(self):
        return self.status == 'completed'

    def ensure_items(self):
        existing = set(self.items.values_list('department', flat=True))
        for code, _ in StudentClearanceItem.DEPARTMENT_CHOICES:
            if code not in existing:
                StudentClearanceItem.objects.create(clearance=self, department=code)


class StudentClearanceItem(models.Model):
    DEPARTMENT_CHOICES = [
        ('library', 'کتابخانه'),
        ('finance', 'مالی / شهریه'),
        ('education', 'آموزش'),
        ('lab', 'آزمایشگاه'),
        ('security', 'حراست'),
        ('dorm', 'خوابگاه'),
    ]
    ITEM_STATUS = [
        ('pending', 'در انتظار'),
        ('cleared', 'تسویه'),
        ('waived', 'معاف'),
    ]
    clearance = models.ForeignKey(
        StudentClearance, on_delete=models.CASCADE, related_name='items', verbose_name=_('تسویه'),
    )
    department = models.CharField(_('واحد'), max_length=20, choices=DEPARTMENT_CHOICES)
    status = models.CharField(_('وضعیت'), max_length=20, choices=ITEM_STATUS, default='pending')
    cleared_at = models.DateTimeField(_('تاریخ'), blank=True, null=True)
    note = models.CharField(_('یادداشت'), max_length=300, blank=True)

    class Meta:
        verbose_name = _('مورد تسویه')
        verbose_name_plural = _('موارد تسویه')
        unique_together = ['clearance', 'department']
        ordering = ['id']

    def __str__(self):
        return f'{self.get_department_display()} — {self.get_status_display()}'

    def save(self, *args, **kwargs):
        from django.utils import timezone
        if self.status in ('cleared', 'waived') and not self.cleared_at:
            self.cleared_at = timezone.now()
        if self.status == 'pending':
            self.cleared_at = None
        super().save(*args, **kwargs)
        self.clearance.refresh_status()


class StudentLifecycleRequest(models.Model):
    """درخواست فارغ‌التحصیلی / انصراف / مرخصی (تأیید ادمین)."""
    TYPE_CHOICES = [
        ('graduation', 'فارغ‌التحصیلی'),
        ('withdrawal', 'انصراف از تحصیل'),
        ('leave', 'مرخصی تحصیلی'),
    ]
    STATUS_CHOICES = [
        ('draft', 'پیش‌نویس'),
        ('submitted', 'ارسال‌شده'),
        ('under_review', 'در حال بررسی'),
        ('approved', 'تأیید شده'),
        ('rejected', 'رد شده'),
        ('cancelled', 'لغو شده'),
    ]
    student = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='lifecycle_requests', verbose_name=_('دانشجو'),
    )
    request_type = models.CharField(_('نوع درخواست'), max_length=20, choices=TYPE_CHOICES)
    status = models.CharField(_('وضعیت'), max_length=20, choices=STATUS_CHOICES, default='draft')
    reason = models.TextField(_('دلیل / توضیحات'), blank=True)
    attachment = models.FileField(
        _('پیوست'), upload_to='lifecycle/', blank=True, null=True,
    )
    admin_response = models.TextField(_('پاسخ ادمین'), blank=True)
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reviewed_lifecycle_requests', verbose_name=_('بررسی‌کننده'),
    )
    reviewed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('درخواست پایان مسیر تحصیلی')
        verbose_name_plural = _('درخواست‌های پایان مسیر تحصیلی')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.student} — {self.get_request_type_display()} ({self.get_status_display()})'

    @property
    def needs_clearance(self):
        return self.request_type in ('graduation', 'withdrawal')

    def apply_approval(self, reviewer=None, note=''):
        """تأیید و به‌روزرسانی وضعیت تحصیلی دانشجو."""
        from django.utils import timezone
        from accounts.models import UserProfile

        mapping = {
            'graduation': 'graduated',
            'withdrawal': 'withdrawn',
            'leave': 'leave',
        }
        new_status = mapping.get(self.request_type)
        if not new_status:
            return
        profile, _ = UserProfile.objects.get_or_create(user=self.student)
        profile.academic_status = new_status
        profile.status_changed_at = timezone.now()
        if note:
            profile.status_note = note[:300]
        elif self.admin_response:
            profile.status_note = self.admin_response[:300]
        profile.save(update_fields=['academic_status', 'status_changed_at', 'status_note', 'updated_at'])
        self.status = 'approved'
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        if note:
            self.admin_response = note
        self.save(update_fields=[
            'status', 'reviewed_by', 'reviewed_at', 'admin_response', 'updated_at',
        ])
