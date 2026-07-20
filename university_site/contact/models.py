from django.db import models
from django.utils.translation import gettext_lazy as _


class ContactMessage(models.Model):
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
    ]
    full_name = models.CharField(_('نام و نام خانوادگی'), max_length=200)
    email = models.EmailField()
    phone = models.CharField(_('تلفن'), max_length=15, blank=True)
    subject = models.CharField(_('موضوع'), max_length=20, choices=SUBJECT_CHOICES, default='general')
    message = models.TextField(_('پیام'))
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
