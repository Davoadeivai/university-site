from django.db import models
from django.utils.translation import gettext_lazy as _

from core.imaging import ShrinkImagesMixin


class ContactMessage(ShrinkImagesMixin, models.Model):
    # عکس فیش را دانشجو با گوشی می‌گیرد؛ خام‌ش چند مگابایت است و
    # صدها تای آن، دیسک سرور را می‌خورد. ۱۶۰۰ پیکسل برای خواندن
    # شمارهٔ پیگیری و مبلغ بیش از کافی است.
    shrink_images = {'attachment': 1600}

    STATUS_CHOICES = [
        ('new', 'جدید'),
        ('read', 'خوانده شده'),
        ('replied', 'پاسخ داده شده'),
        ('closed', 'بسته شده'),
    ]
    SUBJECT_CHOICES = [
        ('general', 'عمومی'),
        ('academic', 'آموزشی'),
        ('admission', 'پذیرش'),
        ('financial', 'مالی'),
        ('technical', 'فنی'),
        ('complaint', 'شکایت'),
        ('suggestion', 'پیشنهاد'),
        ('presidency', 'ارتباط با ریاست'),
        ('tuition_receipt', 'ارسال فیش واریزی شهریه'),
    ]

    # موضوعی که فیش می‌خواهد. در یک جا نوشته می‌شود تا نما، قالب و
    # ادمین هر سه از همین بخوانند و با هم اختلاف پیدا نکنند.
    RECEIPT_SUBJECT = 'tuition_receipt'

    # هیچ‌کدام اجباری نیستند — خواستهٔ موسسه بود که ستاره‌ها برداشته
    # شوند. مدل هم باید همان را بگوید، وگرنه پنل ادمین ردیفی را که
    # خودِ سایت پذیرفته، هنگام ویرایش رد می‌کند.
    full_name = models.CharField(
        _('نام و نام خانوادگی'), max_length=200, blank=True)
    email = models.EmailField(_('ایمیل'), blank=True)
    phone = models.CharField(_('تلفن'), max_length=15, blank=True)
    subject = models.CharField(_('موضوع'), max_length=20, choices=SUBJECT_CHOICES, default='general')
    message = models.TextField(_('پیام'), blank=True)

    # بدون شمارهٔ دانشجویی، فیش برای امور مالی بی‌مصرف است: عکسِ یک
    # واریز که معلوم نیست به حساب چه کسی بنشیند. در فرم، همراه فیش
    # الزامی می‌شود.
    student_number = models.CharField(
        _('شماره دانشجویی'), max_length=20, blank=True)
    national_id = models.CharField(_('کد ملی'), max_length=10, blank=True)
    attachment = models.ImageField(
        _('تصویر پیوست'), upload_to='contact/receipts/%Y/%m/',
        blank=True, null=True,
        help_text=_('فیش واریزی یا هر تصویر پیوست دیگر.'))

    status = models.CharField(_('وضعیت'), max_length=20, choices=STATUS_CHOICES, default='new')
    reply = models.TextField(_('پاسخ'), blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('پیام تماس')
        verbose_name_plural = _('پیام‌های تماس')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name} - {self.get_subject_display()}"


class Alumni(models.Model):
    full_name = models.CharField(_('نام و نام خانوادگی'), max_length=200)
    graduation_year = models.PositiveIntegerField(_('سال فارغ‌التحصیلی'))
    major = models.CharField(_('رشته'), max_length=200)
    degree = models.CharField(_('مقطع'), max_length=100)
    current_position = models.CharField(_('سمت فعلی'), max_length=300, blank=True)
    company = models.CharField(_('شرکت/سازمان'), max_length=200, blank=True)
    photo = models.ImageField(upload_to='alumni/', blank=True, null=True)
    linkedin = models.URLField(blank=True)
    success_story = models.TextField(_('داستان موفقیت'), blank=True)
    is_featured = models.BooleanField(_('برجسته'), default=False)

    class Meta:
        verbose_name = _('فارغ‌التحصیل')
        verbose_name_plural = _('فارغ‌التحصیلان')
        ordering = ['-graduation_year']

    def __str__(self):
        return f"{self.full_name} ({self.graduation_year})"
