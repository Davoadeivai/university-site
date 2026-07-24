from django.db import models
from django.utils.translation import gettext_lazy as _


class SiteSettings(models.Model):
    university_name_fa = models.CharField(_('نام دانشگاه (فارسی)'), max_length=200, default='موسسه آموزش عالی علامه امینی بهنمیر')
    university_name_en = models.CharField(
        _('نام دانشگاه (انگلیسی)'), max_length=200,
        default='Allameh Amini Higher Education Institute',
    )
    logo = models.ImageField(_('لوگو'), upload_to='site/', blank=True, null=True)
    favicon = models.ImageField(_('فاویکون'), upload_to='site/', blank=True, null=True)
    address = models.TextField(_('آدرس'), blank=True)
    phone = models.CharField(_('تلفن'), max_length=50, blank=True)
    fax = models.CharField(_('فکس'), max_length=50, blank=True)
    email = models.EmailField(_('ایمیل'), blank=True)
    postal_code = models.CharField(_('کد پستی'), max_length=20, blank=True)
    telegram = models.URLField(_('تلگرام'), blank=True)
    instagram = models.URLField(_('اینستاگرام'), blank=True)
    twitter = models.URLField(_('توییتر'), blank=True)
    linkedin = models.URLField(_('لینکدین'), blank=True)
    youtube = models.URLField(_('یوتیوب'), blank=True)
    about_short = models.TextField(_('معرفی کوتاه'), blank=True)
    working_hours = models.CharField(_('ساعت کاری'), max_length=200, blank=True)
    map_embed = models.TextField(_('کد نقشه'), blank=True)
    established_year = models.CharField(_('سال تأسیس'), max_length=10, blank=True)

    # آمار نوار صفحه اصلی (قابل ویرایش از ادمین)
    stat_students = models.PositiveIntegerField(_('تعداد دانشجوی فعال'), default=5000)
    stat_faculty = models.PositiveIntegerField(_('تعداد عضو هیئت علمی'), default=200)
    stat_majors = models.PositiveIntegerField(_('تعداد رشته تحصیلی'), default=50)
    stat_years = models.PositiveIntegerField(_('سال سابقه'), default=30)

    # لینک سامانه‌های خارجی مطابق سایت رسمی
    external_lms_url = models.URLField(
        _('لینک سامانه آموزشی خارجی'), blank=True,
        help_text=_('مثلاً سامانه خدمات آموزشی samaweb'),
    )
    external_admin_url = models.URLField(
        _('لینک اتوماسیون اداری'), blank=True,
        help_text=_('سامانه مکاتبات/اتوماسیون اداری'),
    )
    external_publications_url = models.URLField(_('لینک سامانه نشریات'), blank=True)

    # About page content
    history_text = models.TextField(_('تاریخچه دانشگاه'), blank=True)
    vision_text = models.TextField(_('چشم‌انداز'), blank=True)
    mission_text = models.TextField(_('مأموریت'), blank=True)
    values_text = models.TextField(_('ارزش‌ها'), blank=True)

    class Meta:
        verbose_name = _('تنظیمات سایت')
        verbose_name_plural = _('تنظیمات سایت')

    def __str__(self):
        return self.university_name_fa


class Slider(models.Model):
    BADGE_COLOR_CHOICES = [
        ('danger',  'قرمز (فوری)'),
        ('warning', 'زرد (هشدار)'),
        ('success', 'سبز (اطلاع)'),
        ('info',    'آبی روشن'),
        ('primary', 'آبی'),
        ('gold',    'طلایی'),
        ('dark',    'تیره'),
    ]
    title = models.CharField(_('عنوان'), max_length=200)
    subtitle = models.CharField(_('زیرعنوان'), max_length=400, blank=True)
    image = models.ImageField(_('تصویر'), upload_to='sliders/')
    # دکمه اول (اصلی)
    link = models.CharField(_('لینک دکمه اول'), max_length=300, blank=True)
    link_text = models.CharField(_('متن دکمه اول'), max_length=100, blank=True)
    # دکمه دوم
    btn2_text = models.CharField(_('متن دکمه دوم'), max_length=80, blank=True)
    btn2_url = models.CharField(_('لینک دکمه دوم'), max_length=300, blank=True)
    badge_text = models.CharField(
        _('متن اعلان مهم'), max_length=150, blank=True,
        help_text=_('این متن به صورت برچسب روی تصویر اسلایدر نمایش داده می‌شود')
    )
    badge_color = models.CharField(
        _('رنگ اعلان'), max_length=20, choices=BADGE_COLOR_CHOICES,
        default='danger', blank=True,
        help_text=_('رنگ پس‌زمینه برچسب اعلان')
    )
    badge_icon = models.CharField(
        _('آیکون اعلان (FontAwesome)'), max_length=80, blank=True,
        default='fas fa-bell',
        help_text=_('مثال: fas fa-calendar-alt  یا  fas fa-bell')
    )
    order = models.PositiveIntegerField(_('ترتیب'), default=0)
    is_active = models.BooleanField(_('فعال'), default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('اسلایدر')
        verbose_name_plural = _('اسلایدرها')
        ordering = ['order']

    def __str__(self):
        return self.title


# LandingSlider حذف شد — همه اسلایدها در Slider یکپارچه شدند.


class QuickLink(models.Model):
    CATEGORY_CHOICES = [
        ('eservice', _('خدمات الکترونیکی')),
        ('quick_access', _('دسترسی سریع')),
        ('home', _('صفحه اصلی')),
    ]
    title = models.CharField(_('عنوان'), max_length=100)
    icon = models.CharField(_('آیکون (FontAwesome)'), max_length=100, default='fas fa-link')
    url = models.CharField(_('آدرس'), max_length=300)
    category = models.CharField(
        _('دسته'), max_length=20, choices=CATEGORY_CHOICES, default='home',
    )
    color = models.CharField(_('رنگ'), max_length=20, default='primary')
    open_in_new_tab = models.BooleanField(_('باز شدن در تب جدید'), default=False)
    order = models.PositiveIntegerField(_('ترتیب'), default=0)
    is_active = models.BooleanField(_('فعال'), default=True)

    class Meta:
        verbose_name = _('دسترسی سریع')
        verbose_name_plural = _('دسترسی‌های سریع')
        ordering = ['category', 'order']

    def __str__(self):
        return self.title


class Event(models.Model):
    title = models.CharField(_('عنوان رویداد'), max_length=200)
    description = models.TextField(_('توضیحات'))
    date = models.DateField(_('تاریخ'))
    time = models.TimeField(_('ساعت'), blank=True, null=True)
    location = models.CharField(_('مکان'), max_length=200, blank=True)
    image = models.ImageField(_('تصویر'), upload_to='events/', blank=True, null=True)
    link = models.URLField(_('لینک'), blank=True)
    is_featured = models.BooleanField(_('برجسته'), default=False)
    is_active = models.BooleanField(_('فعال'), default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('رویداد')
        verbose_name_plural = _('رویدادها')
        ordering = ['date']

    def __str__(self):
        return self.title


class FAQ(models.Model):
    CATEGORY_CHOICES = [
        ('general', _('عمومی')),
        ('admission', _('پذیرش')),
        ('academic', _('آموزشی')),
        ('financial', _('مالی')),
        ('research', _('پژوهشی')),
    ]
    question = models.CharField(_('سوال'), max_length=500)
    answer = models.TextField(_('پاسخ'))
    category = models.CharField(_('دسته‌بندی'), max_length=20, choices=CATEGORY_CHOICES, default='general')
    order = models.PositiveIntegerField(_('ترتیب'), default=0)
    is_active = models.BooleanField(_('فعال'), default=True)

    class Meta:
        verbose_name = _('سوال متداول')
        verbose_name_plural = _('سوالات متداول')
        ordering = ['category', 'order']

    def __str__(self):
        return self.question


class PageView(models.Model):
    path = models.CharField(max_length=500)
    ip = models.GenericIPAddressField(null=True, blank=True)
    date = models.DateField(auto_now_add=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        verbose_name = _('بازدید')
        verbose_name_plural = _('بازدیدها')


class InstitutionGoal(models.Model):
    GOAL_TYPE_CHOICES = [
        ('strategic', _('هدف راهبردی')),
        ('educational', _('هدف آموزشی')),
        ('research', _('هدف پژوهشی')),
        ('cultural', _('هدف فرهنگی')),
        ('social', _('هدف اجتماعی')),
    ]
    title = models.CharField(_('عنوان هدف'), max_length=300)
    description = models.TextField(_('شرح هدف'), blank=True)
    goal_type = models.CharField(_('نوع هدف'), max_length=20, choices=GOAL_TYPE_CHOICES, default='strategic')
    icon = models.CharField(_('آیکون'), max_length=100, default='fas fa-bullseye', blank=True)
    order = models.PositiveIntegerField(_('ترتیب'), default=0)
    is_active = models.BooleanField(_('فعال'), default=True)

    class Meta:
        verbose_name = _('هدف موسسه')
        verbose_name_plural = _('اهداف موسسه')
        ordering = ['goal_type', 'order']

    def __str__(self):
        return self.title


class BoardMember(models.Model):
    BOARD_TYPE_CHOICES = [
        ('founder', _('هیات موسس')),
        ('trustee', _('هیات امنا')),
    ]
    board_type = models.CharField(_('نوع هیات'), max_length=20, choices=BOARD_TYPE_CHOICES)
    full_name = models.CharField(_('نام و نام خانوادگی'), max_length=200)
    title = models.CharField(_('عنوان/سمت'), max_length=300, blank=True)
    photo = models.ImageField(_('تصویر'), upload_to='board_members/', blank=True, null=True)
    bio = models.TextField(_('بیوگرافی'), blank=True)
    education = models.CharField(_('تحصیلات'), max_length=300, blank=True)
    specialization = models.CharField(_('تخصص'), max_length=300, blank=True)
    email = models.EmailField(_('ایمیل'), blank=True)
    order = models.PositiveIntegerField(_('ترتیب'), default=0)
    is_active = models.BooleanField(_('فعال'), default=True)

    class Meta:
        verbose_name = _('عضو هیات')
        verbose_name_plural = _('اعضای هیات')
        ordering = ['board_type', 'order']

    def __str__(self):
        return f"{self.get_board_type_display()} - {self.full_name}"


class CityInfo(models.Model):
    title = models.CharField(_('عنوان بخش'), max_length=200)
    content = models.TextField(_('محتوا'))
    image = models.ImageField(_('تصویر'), upload_to='city/', blank=True, null=True)
    icon = models.CharField(_('آیکون'), max_length=100, default='fas fa-city', blank=True)
    order = models.PositiveIntegerField(_('ترتیب'), default=0)
    is_active = models.BooleanField(_('فعال'), default=True)

    class Meta:
        verbose_name = _('اطلاعات شهر')
        verbose_name_plural = _('اطلاعات شهر')
        ordering = ['order']

    def __str__(self):
        return self.title


class CityAttraction(models.Model):
    name = models.CharField(_('نام جاذبه'), max_length=200)
    description = models.TextField(_('توضیحات'), blank=True)
    image = models.ImageField(_('تصویر'), upload_to='city/attractions/', blank=True, null=True)
    category = models.CharField(_('دسته‌بندی'), max_length=100, blank=True,
                                 help_text=_('مثلاً: تاریخی، طبیعی، مذهبی، گردشگری'))
    address = models.CharField(_('آدرس'), max_length=300, blank=True)
    order = models.PositiveIntegerField(_('ترتیب'), default=0)
    is_active = models.BooleanField(_('فعال'), default=True)

    class Meta:
        verbose_name = _('جاذبه گردشگری')
        verbose_name_plural = _('جاذبه‌های گردشگری')
        ordering = ['order']

    def __str__(self):
        return self.name


# ─── حوزه ریاست ───────────────────────────────────────────────

class PresidencyOffice(models.Model):
    """اطلاعات دفتر ریاست دانشگاه"""
    president_name = models.CharField(_('نام رئیس'), max_length=200, blank=True)
    president_title = models.CharField(_('درجه علمی / عنوان'), max_length=300, blank=True)
    president_photo = models.ImageField(_('تصویر رئیس'), upload_to='presidency/', blank=True, null=True)
    president_bio = models.TextField(_('بیوگرافی'), blank=True)
    president_education = models.TextField(_('سوابق تحصیلی'), blank=True)
    president_resume = models.TextField(_('سوابق اجرایی'), blank=True)
    president_email = models.EmailField(_('ایمیل'), blank=True)
    president_phone = models.CharField(_('تلفن'), max_length=50, blank=True)
    president_message = models.TextField(_('پیام رئیس'), blank=True)
    office_manager_name = models.CharField(_('مدیر دفتر ریاست'), max_length=200, blank=True)
    office_duties = models.TextField(_('شرح وظایف دفتر ریاست'), blank=True)
    office_address = models.TextField(_('آدرس دفتر'), blank=True)
    office_phone = models.CharField(_('تلفن دفتر'), max_length=100, blank=True)
    office_fax = models.CharField(_('فکس'), max_length=100, blank=True)
    office_email = models.EmailField(_('ایمیل دفتر'), blank=True)
    office_hours = models.CharField(_('ساعات کاری'), max_length=200, blank=True)

    class Meta:
        verbose_name = _('دفتر ریاست')
        verbose_name_plural = _('دفتر ریاست')

    def __str__(self):
        return self.president_name or 'دفتر ریاست'


class PresidencyOfficeUnit(models.Model):
    """زیرصفحه‌های دفتر ریاست مطابق سایت رسمی"""
    slug = models.SlugField(_('اسلاگ'), max_length=80, unique=True, allow_unicode=True)
    title = models.CharField(_('عنوان'), max_length=200)
    content = models.TextField(_('محتوا'), blank=True)
    order = models.PositiveIntegerField(_('ترتیب'), default=0)
    is_active = models.BooleanField(_('فعال'), default=True)

    class Meta:
        verbose_name = _('واحد دفتر ریاست')
        verbose_name_plural = _('واحدهای دفتر ریاست')
        ordering = ['order', 'id']

    def __str__(self):
        return self.title


class GraduateStudiesInfo(models.Model):
    """اطلاعات صفحه تحصیلات تکمیلی (تک‌رکوردی)"""
    manager_name = models.CharField(_('مدیر تحصیلات تکمیلی'), max_length=200, blank=True)
    intro = models.TextField(_('معرفی'), blank=True)

    class Meta:
        verbose_name = _('تحصیلات تکمیلی')
        verbose_name_plural = _('تحصیلات تکمیلی')

    def __str__(self):
        return self.manager_name or 'تحصیلات تکمیلی'


class DeputyVice(models.Model):
    """معاونین دانشگاه"""
    VICE_TYPE_CHOICES = [
        ('education', _('معاونت آموزشی')),
        ('research', _('معاونت پژوهشی')),
        ('student', _('معاونت دانشجویی')),
        ('admin_finance', _('معاونت اداری و مالی')),
        ('cultural', _('معاونت فرهنگی')),
        ('planning', _('معاونت برنامه‌ریزی و توسعه')),
        ('international', _('معاونت بین‌الملل')),
    ]
    vice_type = models.CharField(_('نوع معاونت'), max_length=30, choices=VICE_TYPE_CHOICES)
    full_name = models.CharField(_('نام و نام خانوادگی'), max_length=200)
    academic_rank = models.CharField(_('مرتبه علمی'), max_length=200, blank=True)
    photo = models.ImageField(_('تصویر'), upload_to='deputies/', blank=True, null=True)
    bio = models.TextField(_('بیوگرافی'), blank=True)
    education = models.TextField(_('سوابق تحصیلی'), blank=True)
    resume = models.TextField(_('سوابق اجرایی'), blank=True)
    email = models.EmailField(_('ایمیل'), blank=True)
    phone = models.CharField(_('تلفن'), max_length=50, blank=True)
    office = models.CharField(_('اتاق'), max_length=100, blank=True)
    office_description = models.TextField(_('شرح وظایف'), blank=True)
    order = models.PositiveIntegerField(_('ترتیب'), default=0)
    is_active = models.BooleanField(_('فعال'), default=True)

    class Meta:
        verbose_name = _('معاون دانشگاه')
        verbose_name_plural = _('معاونین دانشگاه')
        ordering = ['order']

    def __str__(self):
        return f"{self.get_vice_type_display()} – {self.full_name}"


class InternationalOffice(models.Model):
    """دفتر همکاری‌های علمی و بین‌الملل"""
    description = models.TextField(_('معرفی دفتر'), blank=True)
    manager_name = models.CharField(_('مدیر دفتر'), max_length=200, blank=True)
    manager_photo = models.ImageField(_('تصویر مدیر'), upload_to='international/', blank=True, null=True)
    manager_email = models.EmailField(_('ایمیل مدیر'), blank=True)
    manager_phone = models.CharField(_('تلفن مدیر'), max_length=50, blank=True)
    phone = models.CharField(_('تلفن دفتر'), max_length=100, blank=True)
    email = models.EmailField(_('ایمیل دفتر'), blank=True)
    address = models.TextField(_('آدرس'), blank=True)

    class Meta:
        verbose_name = _('دفتر بین‌الملل')
        verbose_name_plural = _('دفتر بین‌الملل')

    def __str__(self):
        return 'دفتر بین‌الملل'


class InternationalActivity(models.Model):
    """فعالیت‌های دفتر بین‌الملل"""
    ACTIVITY_TYPE = [
        ('agreement', _('تفاهم‌نامه')),
        ('exchange', _('تبادل دانشجو')),
        ('joint_research', _('پژوهش مشترک')),
        ('conference', _('کنفرانس بین‌المللی')),
        ('scholarship', _('بورسیه')),
    ]
    title = models.CharField(_('عنوان'), max_length=300)
    activity_type = models.CharField(_('نوع'), max_length=20, choices=ACTIVITY_TYPE, default='agreement')
    description = models.TextField(_('توضیحات'), blank=True)
    partner_institution = models.CharField(_('موسسه طرف قرارداد'), max_length=300, blank=True)
    country = models.CharField(_('کشور'), max_length=100, blank=True)
    date = models.DateField(_('تاریخ'), blank=True, null=True)
    document = models.FileField(_('سند / فایل'), upload_to='international/docs/', blank=True, null=True)
    is_active = models.BooleanField(_('فعال'), default=True)
    order = models.PositiveIntegerField(_('ترتیب'), default=0)

    class Meta:
        verbose_name = _('فعالیت بین‌الملل')
        verbose_name_plural = _('فعالیت‌های بین‌الملل')
        ordering = ['-date', 'order']

    def __str__(self):
        return self.title


class PublicRelations(models.Model):
    """مدیریت روابط عمومی"""
    description = models.TextField(_('معرفی روابط عمومی'), blank=True)
    manager_name = models.CharField(_('مدیر روابط عمومی'), max_length=200, blank=True)
    manager_photo = models.ImageField(_('تصویر مدیر'), upload_to='pr/', blank=True, null=True)
    manager_bio = models.TextField(_('بیوگرافی مدیر'), blank=True)
    manager_email = models.EmailField(_('ایمیل'), blank=True)
    manager_phone = models.CharField(_('تلفن'), max_length=50, blank=True)
    phone = models.CharField(_('تلفن روابط عمومی'), max_length=100, blank=True)
    email = models.EmailField(_('ایمیل روابط عمومی'), blank=True)
    address = models.TextField(_('آدرس'), blank=True)
    duties = models.TextField(_('شرح وظایف'), blank=True)

    class Meta:
        verbose_name = _('روابط عمومی')
        verbose_name_plural = _('روابط عمومی')

    def __str__(self):
        return 'مدیریت روابط عمومی'


class PressRelease(models.Model):
    """اطلاعیه‌های روابط عمومی"""
    title = models.CharField(_('عنوان'), max_length=300)
    content = models.TextField(_('متن'))
    image = models.ImageField(_('تصویر'), upload_to='pr/press/', blank=True, null=True)
    published_at = models.DateTimeField(_('تاریخ انتشار'), auto_now_add=True)
    is_active = models.BooleanField(_('فعال'), default=True)

    class Meta:
        verbose_name = _('اطلاعیه روابط عمومی')
        verbose_name_plural = _('اطلاعیه‌های روابط عمومی')
        ordering = ['-published_at']

    def __str__(self):
        return self.title


class SecurityOffice(models.Model):
    """دفتر حراست"""
    description = models.TextField(_('معرفی حراست'), blank=True)
    manager_name = models.CharField(_('مسئول حراست'), max_length=200, blank=True)
    manager_photo = models.ImageField(_('تصویر'), upload_to='security/', blank=True, null=True)
    phone = models.CharField(_('تلفن'), max_length=100, blank=True)
    emergency_phone = models.CharField(_('تلفن اضطراری'), max_length=50, blank=True)
    email = models.EmailField(_('ایمیل'), blank=True)
    address = models.TextField(_('آدرس'), blank=True)
    duties = models.TextField(_('وظایف و مسئولیت‌ها'), blank=True)
    regulations = models.TextField(_('آیین‌نامه‌ها و مقررات'), blank=True)
    working_hours = models.CharField(_('ساعات کاری'), max_length=200, blank=True)

    class Meta:
        verbose_name = _('حراست')
        verbose_name_plural = _('دفتر حراست')

    def __str__(self):
        return 'دفتر حراست'


# ─── معاونت‌ها ────────────────────────────────────────────────

class VicePresidency(models.Model):
    """معاونت‌های دانشگاه — اطلاعات هر معاونت"""
    VICE_TYPE_CHOICES = [
        ('education',     _('معاونت آموزشی و تحصیلات تکمیلی')),
        ('student',       _('معاونت دانشجویی و فرهنگی')),
        ('admin_finance', _('معاونت اداری و مالی')),
        ('construction',  _('معاونت فنی و عمرانی')),
        ('research',      _('معاونت پژوهشی و فناوری')),
        ('development',   _('معاونت توسعه و منابع انسانی')),
    ]
    vice_type      = models.CharField(_('نوع معاونت'), max_length=20, choices=VICE_TYPE_CHOICES, unique=True)
    full_name      = models.CharField(_('نام معاون'), max_length=200, blank=True)
    academic_rank  = models.CharField(_('مرتبه علمی'), max_length=200, blank=True)
    photo          = models.ImageField(_('تصویر'), upload_to='vices/', blank=True, null=True)
    bio            = models.TextField(_('بیوگرافی'), blank=True)
    education      = models.TextField(_('سوابق تحصیلی'), blank=True)
    resume         = models.TextField(_('سوابق اجرایی'), blank=True)
    message        = models.TextField(_('پیام معاون'), blank=True)
    email          = models.EmailField(_('ایمیل'), blank=True)
    phone          = models.CharField(_('تلفن'), max_length=50, blank=True)
    office         = models.CharField(_('اتاق'), max_length=100, blank=True)
    description    = models.TextField(_('معرفی و شرح فعالیت معاونت'), blank=True)
    duties         = models.TextField(_('شرح وظایف'), blank=True)
    goals          = models.TextField(_('اهداف معاونت'), blank=True)
    achievements   = models.TextField(_('دستاوردها'), blank=True)
    is_active      = models.BooleanField(_('فعال'), default=True)

    class Meta:
        verbose_name = _('معاونت')
        verbose_name_plural = _('معاونت‌ها')
        ordering = ['vice_type']

    def __str__(self):
        return self.get_vice_type_display()


class ViceUnit(models.Model):
    """واحدها / ادارات زیرمجموعه هر معاونت"""
    vice     = models.ForeignKey(VicePresidency, on_delete=models.CASCADE,
                                  related_name='units', verbose_name=_('معاونت'))
    name     = models.CharField(_('نام واحد'), max_length=200)
    manager  = models.CharField(_('مدیر / مسئول'), max_length=200, blank=True)
    phone    = models.CharField(_('تلفن'), max_length=50, blank=True)
    email    = models.EmailField(_('ایمیل'), blank=True)
    duties   = models.TextField(_('شرح وظایف'), blank=True)
    location = models.CharField(_('محل'), max_length=200, blank=True)
    order    = models.PositiveIntegerField(_('ترتیب'), default=0)
    is_active = models.BooleanField(_('فعال'), default=True)

    class Meta:
        verbose_name = _('واحد معاونت')
        verbose_name_plural = _('واحدهای معاونت')
        ordering = ['vice', 'order']

    def __str__(self):
        return f"{self.vice.get_vice_type_display()} ← {self.name}"


class ViceAchievement(models.Model):
    """پروژه‌ها / طرح‌های هر معاونت"""
    vice        = models.ForeignKey(VicePresidency, on_delete=models.CASCADE,
                                    related_name='projects', verbose_name=_('معاونت'))
    title       = models.CharField(_('عنوان'), max_length=300)
    description = models.TextField(_('توضیحات'), blank=True)
    status      = models.CharField(_('وضعیت'), max_length=100, blank=True,
                                    help_text=_('مثلاً: در حال اجرا، تکمیل‌شده'))
    year        = models.CharField(_('سال'), max_length=10, blank=True)
    image       = models.ImageField(_('تصویر'), upload_to='vices/projects/', blank=True, null=True)
    is_active   = models.BooleanField(_('فعال'), default=True)
    order       = models.PositiveIntegerField(_('ترتیب'), default=0)

    class Meta:
        verbose_name = _('دستاورد معاونت')
        verbose_name_plural = _('دستاوردهای معاونت')
        ordering = ['vice', 'order']

    def __str__(self):
        return self.title


# ─── چارت سازمانی ───────────────────────────────────────────────

class OrganizationalChart(models.Model):
    """چارت سازمانی دانشگاه - ساختار درختی"""
    NODE_TYPE_CHOICES = [
        ('president', _('ریاست دانشگاه')),
        ('vice', _('معاونت')),
        ('unit', _('واحد/اداره')),
        ('department', _('دانشکده')),
        ('group', _('گروه آموزشی')),
        ('office', _('دفتر')),
        ('section', _('بخش')),
    ]
    
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True,
                              related_name='children', verbose_name=_('والد'))
    node_type = models.CharField(_('نوع واحد'), max_length=20, choices=NODE_TYPE_CHOICES)
    name = models.CharField(_('نام واحد'), max_length=200)
    title = models.CharField(_('عنوان/سمت'), max_length=300, blank=True)
    person_name = models.CharField(_('نام مسئول'), max_length=200, blank=True)
    person_photo = models.ImageField(_('تصویر مسئول'), upload_to='org_chart/', blank=True, null=True)
    person_email = models.EmailField(_('ایمیل'), blank=True)
    person_phone = models.CharField(_('تلفن'), max_length=50, blank=True)
    description = models.TextField(_('شرح وظایف'), blank=True)
    location = models.CharField(_('محل'), max_length=200, blank=True)
    staff_count = models.PositiveIntegerField(_('تعداد پرسنل'), default=0, blank=True)
    order = models.PositiveIntegerField(_('ترتیب نمایش'), default=0)
    is_active = models.BooleanField(_('فعال'), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('چارت سازمانی')
        verbose_name_plural = _('چارت سازمانی')
        ordering = ['order', 'name']

    def __str__(self):
        return f"{self.name} ({self.get_node_type_display()})"

    def get_level(self):
        """محاسبه سطح درخت"""
        level = 0
        parent = self.parent
        while parent:
            level += 1
            parent = parent.parent
        return level

    def get_children(self):
        """دریافت فرزندان مستقیم"""
        return self.children.filter(is_active=True).order_by('order', 'name')

    def get_all_descendants(self):
        """دریافت تمام نسل‌ها (فرزندان و نوه‌ها)"""
        descendants = []
        for child in self.children.all():
            descendants.append(child)
            descendants.extend(child.get_all_descendants())
        return descendants


# ─── حساب بانکی و شناسه واریز (مشابه aab.ac.ir/sh.html) ─────────

class BankAccount(models.Model):
    """شماره حساب‌های موسسه برای واریز شهریه و سایر موارد"""
    title = models.CharField(_('عنوان'), max_length=200)
    bank_name = models.CharField(_('نام بانک'), max_length=100)
    account_number = models.CharField(_('شماره حساب'), max_length=50)
    iban = models.CharField(_('شبا'), max_length=34, blank=True)
    account_holder = models.CharField(_('صاحب حساب'), max_length=200, blank=True)
    description = models.TextField(_('توضیحات'), blank=True)
    order = models.PositiveIntegerField(_('ترتیب'), default=0)
    is_active = models.BooleanField(_('فعال'), default=True)

    class Meta:
        verbose_name = _('حساب بانکی')
        verbose_name_plural = _('حساب‌های بانکی')
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.title} — {self.bank_name}"


class PaymentIdentifier(models.Model):
    """شناسه واریز شهریه دانشجو (جستجو با کد ملی / شماره دانشجویی)"""
    full_name = models.CharField(_('نام و نام خانوادگی'), max_length=200)
    national_id = models.CharField(_('کد ملی'), max_length=10, db_index=True)
    student_number = models.CharField(_('شماره دانشجویی'), max_length=30, blank=True, db_index=True)
    payment_id = models.CharField(_('شناسه واریز'), max_length=50)
    academic_year = models.CharField(_('سال تحصیلی'), max_length=20, blank=True)
    note = models.CharField(_('یادداشت'), max_length=300, blank=True)
    is_active = models.BooleanField(_('فعال'), default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('شناسه واریز')
        verbose_name_plural = _('شناسه‌های واریز')
        ordering = ['full_name']

    def __str__(self):
        return f"{self.full_name} — {self.payment_id}"


# ─── آیین‌نامه‌ها و فرم‌ها ───────────────────────────────────────

def _safe_upload_filename(filename):
    """نام فایل را برای filesystem سرور (ASCII) امن می‌کند؛ پسوند حفظ می‌شود."""
    import os
    import re
    import uuid
    from django.utils.text import get_valid_filename

    filename = get_valid_filename(filename or 'file')
    name, ext = os.path.splitext(filename)
    ext = (ext or '').lower()[:12]
    # فقط حروف/عدد انگلیسی و خط تیره
    safe = re.sub(r'[^A-Za-z0-9_-]+', '-', name).strip('-_')
    if not safe or not re.search(r'[A-Za-z0-9]', safe):
        safe = f'doc-{uuid.uuid4().hex[:10]}'
    return f'{safe[:80]}{ext}'


def _document_pdf_upload_to(instance, filename):
    return f'documents/{_safe_upload_filename(filename)}'


def _document_word_upload_to(instance, filename):
    return f'documents/word/{_safe_upload_filename(filename)}'


class DownloadableDocument(models.Model):
    """فایل‌های قابل دانلود: آیین‌نامه، فرم، راهنما — گروه‌بندی بر اساس مقطع"""
    CATEGORY_CHOICES = [
        ('regulation', _('آیین‌نامه')),
        ('form', _('فرم')),
        ('guide', _('راهنما')),
        ('other', _('سایر')),
    ]
    SECTION_CHOICES = [
        ('', _('عمومی')),
        ('graduate', _('تحصیلات تکمیلی')),
    ]
    DEGREE_LEVEL_CHOICES = [
        ('general', _('عمومی (بدون پوشه مقطع)')),
        ('master', _('کارشناسی ارشد')),
        ('bachelor_continuous', _('کارشناسی پیوسته')),
        ('bachelor_discontinuous', _('کارشناسی ناپیوسته')),
        ('associate', _('کاردانی ناپیوسته')),
        ('associate_tech', _('کاردانی فنی')),
    ]
    title = models.CharField(_('عنوان'), max_length=300)
    category = models.CharField(_('دسته'), max_length=20, choices=CATEGORY_CHOICES, default='form')
    section = models.CharField(
        _('بخش'), max_length=20, choices=SECTION_CHOICES, blank=True, default='',
        help_text=_('مثلاً آیین‌نامه/فرم ویژه تحصیلات تکمیلی'),
    )
    degree_level = models.CharField(
        _('مقطع / پوشه'), max_length=40, choices=DEGREE_LEVEL_CHOICES, default='general',
        help_text=_('سند در کدام پوشه مقطع نمایش داده شود — حتماً یکی را انتخاب کنید'),
        db_index=True,
    )
    description = models.TextField(_('توضیحات'), blank=True)
    file = models.FileField(_('فایل PDF'), upload_to=_document_pdf_upload_to, blank=True, null=True)
    word_file = models.FileField(_('فایل Word'), upload_to=_document_word_upload_to, blank=True, null=True)
    external_url = models.URLField(_('لینک خارجی'), blank=True,
                                   help_text=_('اگر فایل آپلود نشده، از این لینک استفاده می‌شود'))
    order = models.PositiveIntegerField(_('ترتیب'), default=0)
    is_active = models.BooleanField(_('فعال'), default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('آیین‌نامه / فرم')
        verbose_name_plural = _('آیین‌نامه‌ها و فرم‌ها')
        ordering = ['degree_level', 'section', 'category', 'order', '-created_at']

    def __str__(self):
        return self.title

    @property
    def download_url(self):
        if self.file:
            return self.file.url
        return self.external_url or ''

    @classmethod
    def degree_folder_meta(cls):
        """پوشه‌های مقطع برای نمایش در سایت (به‌ترتیب)."""
        icons = {
            'master': 'fas fa-user-graduate',
            'bachelor_continuous': 'fas fa-graduation-cap',
            'bachelor_discontinuous': 'fas fa-book-reader',
            'associate': 'fas fa-certificate',
            'associate_tech': 'fas fa-cogs',
            'general': 'fas fa-folder-open',
        }
        folders = []
        for key, label in cls.DEGREE_LEVEL_CHOICES:
            if key == 'general':
                continue
            folders.append({
                'key': key,
                'label': label,
                'icon': icons.get(key, 'fas fa-folder'),
            })
        folders.append({
            'key': 'general',
            'label': 'عمومی و سایر فایل‌ها',
            'icon': icons['general'],
        })
        return folders
