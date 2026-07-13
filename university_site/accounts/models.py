from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('student', 'دانشجو'),
        ('professor', 'استاد'),
        ('staff', 'کارمند'),
        ('admin', 'مدیر'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(_('نقش'), max_length=20, choices=ROLE_CHOICES, default='student')
    avatar = models.ImageField(_('عکس پروفایل'), upload_to='avatars/', blank=True, null=True)
    phone = models.CharField(_('تلفن'), max_length=15, blank=True)
    student_id = models.CharField(_('شماره دانشجویی/کارمندی'), max_length=50, blank=True)
    department = models.CharField(_('دانشکده/واحد'), max_length=200, blank=True)
    bio = models.TextField(_('بیوگرافی'), blank=True)
    national_id = models.CharField(_('کد ملی'), max_length=10, blank=True)
    birth_date = models.DateField(_('تاریخ تولد'), blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('پروفایل')
        verbose_name_plural = _('پروفایل‌ها')

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_role_display()}"


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
    is_active = models.BooleanField(default=True)
    is_urgent = models.BooleanField(_('فوری'), default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateField(blank=True, null=True)

    class Meta:
        verbose_name = _('اطلاعیه')
        verbose_name_plural = _('اطلاعیه‌ها')
        ordering = ['-created_at']

    def __str__(self):
        return self.title
