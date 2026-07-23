import secrets
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


# ─────────────────────────────────────────────
#  اطلاعات پذیرش (قابل مدیریت از ادمین)
# ─────────────────────────────────────────────
class AdmissionInfo(models.Model):
    DEGREE_CHOICES = [
        ('associate', 'کاردانی'),
        ('bachelor', 'کارشناسی'),
        ('master', 'کارشناسی ارشد'),
        ('phd', 'دکتری'),
    ]
    degree = models.CharField(_('مقطع'), max_length=20, choices=DEGREE_CHOICES, unique=True)
    title = models.CharField(_('عنوان'), max_length=200)
    description = models.TextField(_('توضیحات'), blank=True)
    requirements = models.TextField(_('شرایط پذیرش'))
    tuition_info = models.TextField(_('اطلاعات شهریه'), blank=True)
    documents_required = models.TextField(_('مدارک لازم'), blank=True)
    registration_link = models.URLField(_('لینک ثبت‌نام'), blank=True)
    is_active = models.BooleanField(_('فعال'), default=True)
    deadline = models.DateField(_('مهلت ثبت‌نام'), blank=True, null=True)
    capacity = models.PositiveIntegerField(_('ظرفیت کل'), default=0,
        help_text=_('۰ = نامحدود'))

    class Meta:
        verbose_name = _('اطلاعات پذیرش')
        verbose_name_plural = _('اطلاعات پذیرش')

    def __str__(self):
        return f"پذیرش {self.get_degree_display()}"

    @property
    def is_open(self):
        if not self.is_active:
            return False
        if self.deadline and self.deadline < timezone.now().date():
            return False
        return True


# ─────────────────────────────────────────────
#  درخواست پذیرش — کامل
# ─────────────────────────────────────────────
class Application(models.Model):
    STATUS_CHOICES = [
        ('pending',    'در انتظار بررسی'),
        ('reviewing',  'در حال بررسی'),
        ('incomplete', 'نیاز به تکمیل مدارک'),
        ('interview',  'دعوت به مصاحبه'),
        ('accepted',   'پذیرفته شده'),
        ('rejected',   'رد شده'),
        ('waiting',    'لیست انتظار'),
    ]
    DEGREE_CHOICES = [
        ('associate', 'کاردانی'),
        ('bachelor',  'کارشناسی'),
        ('master',    'کارشناسی ارشد'),
        ('phd',       'دکتری'),
    ]
    GENDER_CHOICES = [('male', 'مرد'), ('female', 'زن')]
    MILITARY_CHOICES = [
        ('done',    'پایان خدمت'),
        ('exempt',  'معافیت'),
        ('student', 'معافیت تحصیلی'),
        ('na',      'مشمول نمی‌شود'),
    ]
    SHIFT_CHOICES = [('day', 'روزانه'), ('evening', 'شبانه'), ('both', 'هر دو')]
    KNOW_FROM_CHOICES = [
        ('social',    'شبکه‌های اجتماعی'),
        ('friend',    'معرفی دوست/آشنا'),
        ('site',      'وب‌سایت دانشگاه'),
        ('exhibition','نمایشگاه'),
        ('other',     'سایر'),
    ]
    PREV_DEGREE_CHOICES = [
        ('diploma',   'دیپلم'),
        ('associate', 'کاردانی'),
        ('bachelor',  'کارشناسی'),
        ('master',    'کارشناسی ارشد'),
    ]

    # ── شناسه یکتا ──
    tracking_code = models.CharField(_('کد رهگیری'), max_length=12, unique=True, blank=True)

    # ── اطلاعات هویتی ──
    first_name  = models.CharField(_('نام'), max_length=100)
    last_name   = models.CharField(_('نام خانوادگی'), max_length=100)
    father_name = models.CharField(_('نام پدر'), max_length=100, blank=True, default='')
    national_id = models.CharField(_('کد ملی'), max_length=10)
    birth_date  = models.DateField(_('تاریخ تولد'), null=True, blank=True)
    gender      = models.CharField(_('جنسیت'), max_length=10, choices=GENDER_CHOICES, default='male')
    military    = models.CharField(_('وضعیت نظام وظیفه'), max_length=20,
                                   choices=MILITARY_CHOICES, default='na', blank=True)

    # ── اطلاعات تماس ──
    phone           = models.CharField(_('موبایل'), max_length=15, blank=True, default='')
    phone_emergency = models.CharField(_('تلفن اضطراری'), max_length=15, blank=True)
    email           = models.EmailField(_('ایمیل'), blank=True)
    address         = models.TextField(_('آدرس'), default='')
    postal_code     = models.CharField(_('کد پستی'), max_length=10, blank=True)

    # ── سوابق تحصیلی ──
    prev_degree        = models.CharField(_('آخرین مدرک'), max_length=20,
                                          choices=PREV_DEGREE_CHOICES, default='diploma')
    prev_major         = models.CharField(_('رشته مدرک قبلی'), max_length=200, blank=True)
    prev_school        = models.CharField(_('نام مدرسه/مرکز'), max_length=200, blank=True)
    prev_grad_year     = models.CharField(_('سال فارغ‌التحصیلی'), max_length=10, blank=True)
    gpa                = models.DecimalField(_('معدل'), max_digits=4, decimal_places=2,
                                             blank=True, null=True)

    # ── رشته درخواستی ──
    degree         = models.CharField(_('مقطع'), max_length=20, choices=DEGREE_CHOICES)
    desired_major  = models.ForeignKey(
        'academics.Major', on_delete=models.PROTECT,
        related_name='applications_priority1', verbose_name=_('اولویت اول رشته'),
    )
    desired_major2 = models.ForeignKey(
        'academics.Major', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='applications_priority2', verbose_name=_('اولویت دوم رشته'),
    )
    shift          = models.CharField(_('ترجیح شیفت'), max_length=10,
                                      choices=SHIFT_CHOICES, default='day')

    # ── آپلود مدارک ──
    doc_national_id = models.ImageField(_('تصویر کارت ملی'),
                                        upload_to='admissions/docs/', blank=True, null=True)
    doc_prev_degree = models.ImageField(_('تصویر مدرک تحصیلی'),
                                        upload_to='admissions/docs/', blank=True, null=True)
    doc_photo       = models.ImageField(_('عکس پرسنلی'),
                                        upload_to='admissions/docs/', blank=True, null=True)
    doc_military    = models.ImageField(_('کارت پایان خدمت/معافیت'),
                                        upload_to='admissions/docs/', blank=True, null=True)

    # ── سایر ──
    know_from      = models.CharField(_('نحوه آشنایی'), max_length=20,
                                      choices=KNOW_FROM_CHOICES, default='site')
    special_needs  = models.TextField(_('نیاز ویژه / شرایط خاص'), blank=True)
    phone_verified = models.BooleanField(_('موبایل تأیید شده'), default=False)
    agreed_terms   = models.BooleanField(_('پذیرش قوانین'), default=False)

    # ── وضعیت و ادمین ──
    status         = models.CharField(_('وضعیت'), max_length=20,
                                      choices=STATUS_CHOICES, default='pending')
    admin_notes    = models.TextField(_('یادداشت کارشناس پذیرش'), blank=True)
    reject_reason  = models.TextField(_('دلیل رد'), blank=True)
    interview_date = models.DateTimeField(_('تاریخ مصاحبه'), blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('درخواست پذیرش')
        verbose_name_plural = _('درخواست‌های پذیرش')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.first_name} {self.last_name} — {self.get_degree_display()} ({self.tracking_code})"

    def save(self, *args, **kwargs):
        if not self.tracking_code:
            self.tracking_code = self._gen_tracking()
        super().save(*args, **kwargs)

    @staticmethod
    def _gen_tracking():
        while True:
            code = f'{secrets.randbelow(900000000000) + 100000000000:012d}'
            if not Application.objects.filter(tracking_code=code).exists():
                return code


# ─────────────────────────────────────────────
#  ساختار شهریه (منبع واحد — متصل به کاتالوگ رشته)
# ─────────────────────────────────────────────
class TuitionStructure(models.Model):
    major = models.ForeignKey(
        'academics.Major',
        on_delete=models.PROTECT,
        related_name='tuition_structures',
        verbose_name=_('رشته'),
    )
    academic_year = models.CharField(_('سال تحصیلی'), max_length=20)
    fixed_fee = models.PositiveBigIntegerField(_('شهریه ثابت (تومان)'), default=0)
    theory_fee = models.PositiveBigIntegerField(_('شهریه هر واحد نظری (تومان)'), default=0)
    practical_fee = models.PositiveBigIntegerField(_('شهریه هر واحد عملی (تومان)'), default=0)
    lab_fee = models.PositiveBigIntegerField(_('شهریه هر واحد عملی‌آزمایشگاهی (تومان)'), default=0)
    registration_fee = models.PositiveBigIntegerField(_('هزینه ثبت‌نام'), default=0)
    insurance_fee = models.PositiveBigIntegerField(_('بیمه دانشجویی'), default=0)
    card_fee = models.PositiveBigIntegerField(_('کارت دانشجویی'), default=0)
    dorm_fee = models.PositiveBigIntegerField(_('خوابگاه (ماهانه)'), default=0)
    notes = models.TextField(_('توضیحات'), blank=True)
    is_active = models.BooleanField(_('فعال'), default=True)

    class Meta:
        verbose_name = _('ساختار شهریه')
        verbose_name_plural = _('ساختار شهریه‌ها')
        ordering = ['-academic_year', 'major__name']
        unique_together = [['major', 'academic_year']]

    def __str__(self):
        return f"{self.major.name} — {self.major.get_degree_display()} ({self.academic_year})"

    @property
    def degree(self):
        return self.major.get_degree_display()

    @property
    def degree_code(self):
        return self.major.degree

    @property
    def major_name(self):
        return self.major.name


# ─────────────────────────────────────────────
#  تخفیف‌ها و بورسیه
# ─────────────────────────────────────────────
class TuitionDiscount(models.Model):
    DISCOUNT_TYPE = [
        ('grade',    'تخفیف رتبه/معدل ممتاز'),
        ('sibling',  'تخفیف خواهر و برادر'),
        ('cash',     'تخفیف پرداخت نقدی/زودهنگام'),
        ('talent',   'بورسیه استعداد درخشان'),
        ('prev_gpa', 'تخفیف/افزایش بر اساس معدل ترم قبل'),
    ]
    discount_type = models.CharField(_('نوع تخفیف'), max_length=20, choices=DISCOUNT_TYPE)
    title         = models.CharField(_('عنوان'), max_length=200)
    percent       = models.PositiveSmallIntegerField(_('درصد تخفیف'), default=0)
    description   = models.TextField(_('شرایط'), blank=True)
    is_active     = models.BooleanField(_('فعال'), default=True)

    class Meta:
        verbose_name = _('تخفیف شهریه')
        verbose_name_plural = _('تخفیف‌ها و بورسیه‌ها')

    def __str__(self):
        return f"{self.title} ({self.percent}%)"


# ─────────────────────────────────────────────
#  قسط شهریه پذیرش (متقاضی) — منبع واحد پرداخت پیش از ثبت‌نام قطعی
# ─────────────────────────────────────────────
class StudentPayment(models.Model):
    STATUS_CHOICES = [
        ('paid',    'پرداخت‌شده'),
        ('pending', 'در انتظار تأیید'),
        ('overdue', 'معوق'),
        ('waived',  'بخشوده‌شده'),
    ]
    application   = models.ForeignKey(Application, on_delete=models.CASCADE,
                                      related_name='payments', verbose_name=_('متقاضی'))
    installment_no= models.PositiveSmallIntegerField(_('شماره قسط'), default=1)
    amount        = models.PositiveBigIntegerField(_('مبلغ (تومان)'))
    due_date      = models.DateField(_('تاریخ سررسید'))
    paid_at       = models.DateTimeField(_('تاریخ پرداخت'), blank=True, null=True)
    receipt       = models.ImageField(_('فیش واریزی'), upload_to='payments/', blank=True, null=True)
    status        = models.CharField(_('وضعیت'), max_length=20,
                                     choices=STATUS_CHOICES, default='pending')
    confirmed_by  = models.CharField(_('تأیید توسط'), max_length=100, blank=True)
    notes         = models.TextField(_('توضیحات'), blank=True)

    class Meta:
        verbose_name = _('قسط شهریه پذیرش')
        verbose_name_plural = _('اقساط شهریه پذیرش')
        ordering = ['due_date']

    def __str__(self):
        return f"قسط {self.installment_no} — {self.application}"

    @property
    def is_overdue(self):
        return self.status != 'paid' and self.due_date < timezone.now().date()


# ─────────────────────────────────────────────
#  کد OTP موبایل برای پذیرش
# ─────────────────────────────────────────────
class AdmissionOTP(models.Model):
    phone = models.CharField(_('شماره موبایل'), max_length=15)
    code = models.CharField(_('کد تأیید'), max_length=6)
    created_at = models.DateTimeField(_('زمان ایجاد'), auto_now_add=True)
    expires_at = models.DateTimeField(_('انقضا'))
    is_used = models.BooleanField(_('استفاده‌شده'), default=False)
    attempts = models.PositiveSmallIntegerField(_('تلاش ناموفق'), default=0)

    class Meta:
        verbose_name = _('کد تأیید پذیرش')
        verbose_name_plural = _('کدهای تأیید پذیرش')
        ordering = ['-created_at']

    def is_valid(self):
        from django.conf import settings as dj_settings
        max_attempts = getattr(dj_settings, 'OTP_MAX_VERIFY_ATTEMPTS', 5)
        return (
            not self.is_used
            and timezone.now() <= self.expires_at
            and self.attempts < max_attempts
        )

    @classmethod
    def create_for_phone(cls, phone):
        cls.objects.filter(phone=phone, is_used=False).update(is_used=True)
        code = f'{secrets.randbelow(1000000):06d}'
        expires = timezone.now() + timezone.timedelta(minutes=10)
        return cls.objects.create(phone=phone, code=code, expires_at=expires)
