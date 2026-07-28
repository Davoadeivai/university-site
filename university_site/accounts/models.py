import secrets
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('student', 'دانشجو'),
        ('professor', 'استاد'),
        ('staff', 'مدیر دانشگاه'),
        ('admin', 'ادمین'),
    ]
    GENDER_CHOICES = [
        ('male', _('مرد')),
        ('female', _('زن')),
    ]
    MILITARY_CHOICES = [
        ('done', _('پایان خدمت')),
        ('exempt', _('معاف')),
        ('studying', _('در حال تحصیل / معافیت تحصیلی')),
        ('na', _('مشمول نیست')),
    ]
    PREV_DEGREE_CHOICES = [
        ('diploma', _('دیپلم')),
        ('associate', _('کاردانی')),
        ('bachelor', _('کارشناسی')),
        ('discontinuous_bachelor', _('کارشناسی ناپیوسته')),
        ('master', _('کارشناسی ارشد')),
    ]
    ACADEMIC_STATUS_CHOICES = [
        ('applicant', _('متقاضی')),
        ('active', _('در حال تحصیل')),
        ('leave', _('مرخصی')),
        ('withdrawn', _('انصراف')),
        ('expelled', _('اخراج')),
        ('graduated', _('فارغ‌التحصیل')),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(_('نقش'), max_length=20, choices=ROLE_CHOICES, default='student')
    academic_status = models.CharField(
        _('وضعیت تحصیلی'),
        max_length=20,
        choices=ACADEMIC_STATUS_CHOICES,
        default='active',
        db_index=True,
    )
    status_changed_at = models.DateTimeField(_('زمان تغییر وضعیت'), blank=True, null=True)
    status_note = models.CharField(_('یادداشت وضعیت'), max_length=300, blank=True)
    avatar = models.ImageField(
        _('عکس پرسنلی'),
        upload_to='avatars/',
        blank=True,
        null=True,
        help_text=_('عکس رسمی ۳×۴؛ برای بانوان با حجاب کامل الزامی است.'),
    )
    photo_hijab_confirmed = models.BooleanField(
        _('تأیید حجاب کامل در عکس'),
        default=False,
        help_text=_('برای بانوان: تأیید می‌کنم عکس با حجاب کامل اسلامی است.'),
    )

    # هویت
    father_name = models.CharField(_('نام پدر'), max_length=100, blank=True)
    phone = models.CharField(_('تلفن'), max_length=15, blank=True)
    phone_emergency = models.CharField(_('تلفن اضطراری'), max_length=15, blank=True)
    student_id = models.CharField(_('شماره دانشجویی/کارمندی'), max_length=50, blank=True)
    department = models.CharField(_('دانشکده/واحد'), max_length=200, blank=True)
    major = models.ForeignKey(
        'academics.Major',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students',
        verbose_name=_('رشته تحصیلی'),
    )
    bio = models.TextField(_('بیوگرافی'), blank=True)
    national_id = models.CharField(_('کد ملی'), max_length=10, blank=True)
    birth_date = models.DateField(_('تاریخ تولد'), blank=True, null=True)
    gender = models.CharField(_('جنسیت'), max_length=10, choices=GENDER_CHOICES, blank=True)
    military = models.CharField(
        _('وضعیت نظام وظیفه'), max_length=20, choices=MILITARY_CHOICES, blank=True, default='na',
    )

    # سکونت
    province = models.CharField(_('استان'), max_length=100, blank=True)
    city = models.CharField(_('شهر'), max_length=100, blank=True)
    address = models.TextField(_('آدرس'), blank=True)
    postal_code = models.CharField(_('کد پستی'), max_length=10, blank=True)

    # سوابق تحصیلی
    prev_degree = models.CharField(
        _('آخرین مدرک'), max_length=30, choices=PREV_DEGREE_CHOICES, blank=True,
    )
    prev_major = models.CharField(_('رشته مدرک قبلی'), max_length=200, blank=True)
    prev_school = models.CharField(_('مدرسه / دانشگاه قبلی'), max_length=200, blank=True)
    prev_grad_year = models.CharField(_('سال فارغ‌التحصیلی'), max_length=10, blank=True)
    gpa = models.DecimalField(
        _('معدل'), max_digits=4, decimal_places=2, blank=True, null=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('پروفایل')
        verbose_name_plural = _('پروفایل‌ها')

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_role_display()}"

    def completeness_percent(self) -> int:
        """درصد تکمیل پروفایل برای نمایش راهنما."""
        checks = [
            bool(self.user.first_name and self.user.last_name),
            bool(self.national_id),
            bool(self.birth_date),
            bool(self.gender),
            bool(self.phone),
            bool(self.address),
            bool(self.city or self.province),
            bool(self.major_id or self.department),
            bool(self.avatar),
            bool(self.gender != 'female' or self.photo_hijab_confirmed),
        ]
        if not checks:
            return 0
        return int(round(100 * sum(1 for c in checks if c) / len(checks)))


class Announcement(models.Model):
    TARGET_CHOICES = [
        ('all', 'همه'),
        ('students', 'دانشجویان'),
        ('professors', 'اساتید'),
        ('staff', 'کارمندان'),
    ]
    title = models.CharField(_('عنوان'), max_length=300)
    content = models.TextField(_('محتوا'))
    target = models.CharField(_('مخاطب'), max_length=20, choices=TARGET_CHOICES, default='all')
    file = models.FileField(_('فایل پیوست'), upload_to='announcements/', blank=True, null=True)
    is_active = models.BooleanField(_('فعال'), default=True)
    is_urgent = models.BooleanField(_('فوری'), default=False)
    created_at = models.DateTimeField(_('زمان ایجاد'), auto_now_add=True)
    expires_at = models.DateField(_('تاریخ انقضا'), blank=True, null=True)

    class Meta:
        verbose_name = _('اطلاعیه')
        verbose_name_plural = _('اطلاعیه‌ها')
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class OTPCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otp_codes', verbose_name=_('کاربر'))
    code = models.CharField(_('کد تأیید'), max_length=6)
    created_at = models.DateTimeField(_('زمان ایجاد'), auto_now_add=True)
    expires_at = models.DateTimeField(_('انقضا'))
    is_used = models.BooleanField(_('استفاده‌شده'), default=False)

    class Meta:
        verbose_name = _('کد تأیید')
        verbose_name_plural = _('کدهای تأیید')
        ordering = ['-created_at']

    def __str__(self):
        # کد خام هرگز اینجا نیاید: این رشته در LogEntry.object_repr ادمین
        # به‌صورت دائمی ذخیره می‌شود و بعد از انقضای کد هم باقی می‌ماند.
        return f"{self.user.username} — کد تأیید {self.pk}"

    def is_valid(self):
        return not self.is_used and timezone.now() <= self.expires_at

    @classmethod
    def create_for_user(cls, user):
        """یک کد ۶ رقمی جدید برای کاربر می‌سازد و کدهای قبلی را باطل می‌کند."""
        cls.objects.filter(user=user, is_used=False).update(is_used=True)
        code = f'{secrets.randbelow(1000000):06d}'
        expires = timezone.now() + timezone.timedelta(minutes=10)
        return cls.objects.create(user=user, code=code, expires_at=expires)
