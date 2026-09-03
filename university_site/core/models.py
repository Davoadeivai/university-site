import os
import re
import uuid

from django.core.validators import (FileExtensionValidator,
                                    MaxValueValidator, MinValueValidator)
from django.db import models
from django.utils.text import get_valid_filename
from django.utils.translation import gettext_lazy as _
from core.filecheck import file_present
from core.imaging import ShrinkImagesMixin


def _safe_upload_filename(filename):
    """نام فایل را برای filesystem سرور (ASCII) امن می‌کند؛ پسوند حفظ می‌شود."""
    filename = get_valid_filename(filename or 'file')
    name, ext = os.path.splitext(filename)
    ext = (ext or '').lower()[:12]
    safe = re.sub(r'[^A-Za-z0-9_-]+', '-', name).strip('-_')
    if not safe or not re.search(r'[A-Za-z0-9]', safe):
        safe = f'doc-{uuid.uuid4().hex[:10]}'
    return f'{safe[:80]}{ext}'


def _org_chart_file_upload_to(instance, filename):
    return f'site/org_chart/{_safe_upload_filename(filename)}'


# سقف اسلایدهای صفحهٔ اصلی.
#
# پیش از این عدد ۵ داخل ویو نوشته شده بود و مدیر هرچه اسلاید ششم و
# هفتم می‌ساخت، در پنل ثبت می‌شد ولی روی صفحه نمی‌آمد و هیچ‌جا هم
# نمی‌گفت چرا. حالا خودِ مدیر تعیینش می‌کند؛ این عدد فقط سقف است،
# چون هر اسلاید یک عکس است و صفحه را سنگین می‌کند.
MAX_HOME_SLIDES = 12


class SiteSettings(models.Model):
    university_name_fa = models.CharField(_('نام دانشگاه (فارسی)'), max_length=200, default='موسسه آموزش عالی علامه امینی')
    university_name_en = models.CharField(
        _('نام دانشگاه (انگلیسی)'), max_length=200,
        default='Allameh Amini Higher Education Institute',
    )
    world_class_url = models.URLField(
        _('نشانی سایت کلاس جهانی'), blank=True,
        default='https://WCM-Society.Com',
        help_text=_(
            'نشان کلاس جهانی در نوار بالای سایت به این نشانی می‌رود.'))
    admission_poster = models.ImageField(
        _('پوستر رشته‌های پذیرش دانشجو'),
        upload_to='site/admission/', blank=True, null=True,
        help_text=_(
            'روی صفحهٔ اصلی یک باکس با همین عنوان می‌آید و با کلیک، '
            'این تصویر تمام‌صفحه نشان داده می‌شود.'))
    about_image = models.ImageField(
        _('تصویر صفحهٔ معرفی موسسه'),
        upload_to='site/about/', blank=True, null=True,
        help_text=_(
            'کنار «تاریخچه مؤسسه» دیده می‌شود. اگر خالی باشد، عکس '
            'پیش‌فرض پردیس نمایش داده می‌شود. نسبت افقی (مثلاً '
            '۱۶۰۰×۹۰۰) بهترین نتیجه را می‌دهد.'))
    faculties_pdf = models.FileField(
        _('فایل رشته‌های دانشکده‌ها (PDF)'),
        upload_to='site/faculties/', blank=True, null=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])],
        help_text=_(
            'صفحهٔ «دانشکده‌ها» همین فایل را نشان می‌دهد. '
            'برای جایگزینی، فایل تازه را آپلود کنید.'))
    home_slider_count = models.PositiveSmallIntegerField(
        _('تعداد اسلاید صفحهٔ اصلی'), default=7,
        validators=[MinValueValidator(1), MaxValueValidator(MAX_HOME_SLIDES)],
        help_text=_(
            'چند اسلاید از فهرست اسلایدها روی صفحهٔ اصلی بیاید. '
            'اسلایدهای بیشتر از این عدد ثبت می‌مانند ولی نمایش داده '
            'نمی‌شوند. هر اسلاید یک عکس است و وزن صفحه را بالا '
            'می‌برد، پس سقف %d گذاشته شده.' % MAX_HOME_SLIDES))
    # ── نوار اول صفحهٔ اصلی: اسلایدر و ستون اطلاع‌رسانی کنارش ──
    #
    # اسلاید تمام‌عرض بود و تا وقتی کسی اسکرول نمی‌کرد، هیچ خبری
    # دیده نمی‌شد. حالا اسلایدر کوتاه‌تر و باریک‌تر است و کنارش یک
    # ستون می‌ماند برای اطلاعیه، خبر و رویداد. هر چهار تصمیم —
    # بودن یا نبودن ستون، ارتفاع اسلاید، پهنای ستون، و اینکه چه
    # فهرست‌هایی در آن بیاید — از همین‌جا کنترل می‌شود.
    hero_height = models.PositiveSmallIntegerField(
        _('ارتفاع اسلایدر (درصد صفحه)'), default=62,
        validators=[MinValueValidator(35), MaxValueValidator(90)],
        help_text=_('عدد کوچک‌تر یعنی تصویر کوچک‌تر. پیش‌فرض ۶۲.'))
    hero_side_enabled = models.BooleanField(
        _('ستون اطلاع‌رسانی کنار اسلایدر'), default=True,
        help_text=_('برداشتن تیک، اسلایدر را دوباره تمام‌عرض می‌کند.'))
    hero_side_width = models.PositiveSmallIntegerField(
        _('پهنای ستون اطلاع‌رسانی (پیکسل)'), default=340,
        validators=[MinValueValidator(240), MaxValueValidator(520)])
    hero_side_count = models.PositiveSmallIntegerField(
        _('تعداد ردیف هر فهرست'), default=4,
        validators=[MinValueValidator(1), MaxValueValidator(10)])
    hero_side_show_announcements = models.BooleanField(
        _('اطلاعیه‌ها در ستون'), default=True)
    hero_side_show_news = models.BooleanField(
        _('اخبار در ستون'), default=True)
    hero_side_show_events = models.BooleanField(
        _('رویدادها در ستون'), default=True)

    council_card_min_width = models.PositiveSmallIntegerField(
        _('حداقل عرض کارت شورا'), default=260,
        validators=[MinValueValidator(180), MaxValueValidator(420)],
        help_text=_(
            'کارت‌های صفحهٔ شوراها حداقل این عرض را می‌گیرند؛ با این مقدار '
            'می‌توانید اندازهٔ باکس‌ها را در فهرست شوراها تنظیم کنید.'))
    council_card_min_height = models.PositiveSmallIntegerField(
        _('حداقل ارتفاع کارت شورا'), default=220,
        validators=[MinValueValidator(150), MaxValueValidator(500)],
        help_text=_(
            'ارتفاع حداقل هر کارت در صفحهٔ شوراها. اگر محتوای یک کارت طولانی‌تر شد، '
            'بلندتر نیز می‌تواند رشد کند.'))
    logo = models.ImageField(_('لوگو'), upload_to='site/', blank=True, null=True)
    favicon = models.ImageField(_('فاویکون'), upload_to='site/', blank=True, null=True)
    world_class_logo = models.ImageField(
        _('نشان کلاس جهانی (WCU)'), upload_to='site/', blank=True, null=True,
        help_text=_(
            'در دو سوی عنوان سربرگ و در صفحهٔ ریاست نمایش داده می‌شود. '
            'ترجیحاً PNG با پس‌زمینهٔ شفاف و مربع.'))
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
    # ── رنگ متن تقویم آموزشی ──
    # اینجاست تا عوض‌کردن رنگ یک ویرایش در پنل باشد، نه یک تغییر در
    # CSS و یک دیپلوی. خالی یعنی «همان رنگ پیش‌فرض قالب».
    CALENDAR_COLOUR_HELP = _(
        'خالی بگذارید تا رنگ پیش‌فرض بماند. مقدار باید شش‌رقمی '
        'هگز باشد، مثل #0d2137.')

    calendar_ink = models.CharField(
        _('رنگ عنوان و تاریخ (حالت روشن)'), max_length=9, blank=True,
        help_text=CALENDAR_COLOUR_HELP)
    calendar_ink_soft = models.CharField(
        _('رنگ توضیحات (حالت روشن)'), max_length=9, blank=True,
        help_text=CALENDAR_COLOUR_HELP)
    calendar_ink_dark = models.CharField(
        _('رنگ عنوان و تاریخ (حالت تیره)'), max_length=9, blank=True,
        help_text=CALENDAR_COLOUR_HELP)
    calendar_ink_soft_dark = models.CharField(
        _('رنگ توضیحات (حالت تیره)'), max_length=9, blank=True,
        help_text=CALENDAR_COLOUR_HELP)

    org_chart_file = models.FileField(
        _('فایل چارت سازمانی'),
        upload_to=_org_chart_file_upload_to,
        blank=True,
        null=True,
        validators=[FileExtensionValidator(
            allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'gif', 'webp', 'doc', 'docx'],
        )],
        help_text=_('PDF، تصویر (JPG/PNG/…) یا Word. برای حذف، تیک «پاک کردن» را بزنید و ذخیره کنید.'),
    )

    class Meta:
        verbose_name = _('تنظیمات سایت')
        verbose_name_plural = _('تنظیمات سایت')

    def __str__(self):
        return self.university_name_fa

    @property
    def calendar_colours(self) -> dict:
        """رنگ‌های تقویم که ادمین گذاشته — فقط مقدارهای معتبر.

        این مقدارها مستقیم داخل یک بلوک <style> می‌نشینند. هر رشتهٔ
        دلخواهی آنجا می‌تواند از اعلان بیرون بزند و قاعدهٔ دیگری
        تزریق کند، پس هرچه شکل هگز نداشته باشد دور ریخته می‌شود —
        نه پاک‌سازی، نه فرار دادن؛ فقط پذیرفتن الگوی درست.
        """
        import re

        pattern = re.compile(r'^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$')
        found = {}
        for key in ('calendar_ink', 'calendar_ink_soft',
                    'calendar_ink_dark', 'calendar_ink_soft_dark'):
            value = (getattr(self, key, '') or '').strip()
            if pattern.match(value):
                found[key] = value
        return found

    @property
    def org_chart_size(self):
        """ابعاد واقعی تصویر چارت، برای width/height تگ img.

        چارت تمام‌عرض است و ارتفاعش از نسبت خودش می‌آید؛ بدون این دو
        عدد، مرورگر تا رسیدن فایل ارتفاع را نمی‌داند و صفحه هنگام
        بارگذاری یک تکان بزرگ می‌خورد.

        خواندن ابعاد یعنی باز کردن فایل — اگر PDF یا Word باشد یا
        روی دیسک نباشد، None برمی‌گردد و دو صفت نوشته نمی‌شوند.
        """
        if not self.org_chart_file or self.org_chart_file_kind != 'image':
            return None
        try:
            from PIL import Image
            with Image.open(self.org_chart_file.path) as image:
                return image.size
        except Exception:                      # noqa: BLE001
            return None

    @property
    def org_chart_file_kind(self):
        """نوع فایل چارت: image | pdf | word | other | None"""
        if not self.org_chart_file:
            return None
        ext = os.path.splitext(self.org_chart_file.name)[1].lower().lstrip('.')
        if ext in ('jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp'):
            return 'image'
        if ext == 'pdf':
            return 'pdf'
        if ext in ('doc', 'docx'):
            return 'word'
        return 'other'


class Slider(ShrinkImagesMixin, models.Model):
    # اسلاید تمام‌عرض است و اولینش eager بار می‌شود؛ ۲۰۰۰ پیکسل
    # روی بزرگ‌ترین نمایشگر هم کافی است و بیش از آن فقط وزن است.
    shrink_images = {'image': 2000}

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


class Event(ShrinkImagesMixin, models.Model):
    shrink_images = {'image': 1400}

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
        verbose_name_plural = _('پرسش‌های متداول')
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


class BoardMember(ShrinkImagesMixin, models.Model):
    shrink_images = {'photo': 800}

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


class CityInfo(ShrinkImagesMixin, models.Model):
    shrink_images = {'image': 1400}

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


class CityAttraction(ShrinkImagesMixin, models.Model):
    shrink_images = {'image': 1200}

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

    # ── حضور علمی بیرون از سایت ──
    # رئیس یک هویت علمی بیرون از این سایت دارد؛ تا امروز جایی برای
    # ثبتش نبود و بازدیدکننده‌ای که دنبال سوابقش می‌گشت باید گوگل
    # می‌کرد.
    president_website = models.URLField(
        _('وب‌سایت / صفحهٔ علمی'), blank=True,
        help_text=_('نشانی کامل با https، مثلاً https://example.com'))
    president_website_label = models.CharField(
        _('عنوان وب‌سایت'), max_length=120, blank=True,
        help_text=_('متنی که روی دکمه دیده می‌شود؛ خالی بماند نام دامنه می‌آید.'))
    # ── لوح کلاس جهانی، زیر نشان WCU در صفحهٔ ریاست ──
    wcu_title = models.CharField(
        _('عنوان سایت تخصصی'), max_length=200, blank=True,
        help_text=_('یک خط، درشت و رنگی زیر نشان کلاس جهانی.'))
    wcu_motto = models.TextField(
        _('شعار سایت تخصصی'), blank=True,
        help_text=_('زیر عنوان، داخل گیومه نمایش داده می‌شود.'))

    president_scholar = models.URLField(_('گوگل اسکولار'), blank=True)
    president_orcid = models.CharField(
        _('شناسهٔ ORCID'), max_length=40, blank=True,
        help_text=_('فقط شناسه، مثلاً 0000-0002-1825-0097'))
    president_research = models.TextField(
        _('زمینه‌های پژوهشی'), blank=True,
        help_text=_('هر زمینه در یک خط جدا؛ برچسب‌وار نمایش داده می‌شود.'))
    president_teaching = models.TextField(
        _('سوابق تدریسی'), blank=True,
        help_text=_('هر درس در یک خط جدا.'))
    president_awards = models.TextField(
        _('جوایز و افتخارات علمی'), blank=True,
        help_text=_('هر مورد در یک خط جدا.'))
    president_memberships = models.TextField(
        _('عضویت در مراکز علمی و پژوهشی'), blank=True,
        help_text=_('هر مورد در یک خط جدا.'))
    president_highlights = models.TextField(
        _('آمار برجسته'), blank=True,
        help_text=_(
            'هر خط به شکل «عدد | برچسب»، مثلاً:<br>'
            '<code>۳۱ | جلد کتاب دانشگاهی</code><br>'
            'بالای رزومه به‌صورت کارت‌های عددی دیده می‌شوند.'))

    office_manager_name = models.CharField(_('مدیر دفتر ریاست'), max_length=200, blank=True)
    office_duties = models.TextField(_('شرح وظایف دفتر ریاست'), blank=True)
    office_address = models.TextField(_('آدرس دفتر'), blank=True)
    office_phone = models.CharField(_('تلفن دفتر'), max_length=100, blank=True)
    office_fax = models.CharField(_('فکس'), max_length=100, blank=True)
    office_email = models.EmailField(_('ایمیل دفتر'), blank=True)
    office_hours = models.CharField(_('ساعات کاری'), max_length=200, blank=True)
    office_floor = models.CharField(
        _('طبقهٔ دفتر ریاست'), max_length=60, blank=True,
        help_text=_(
            'مثلاً «طبقهٔ سوم». پیش از این در قالب ثابت نوشته شده بود و '
            'با نشانیِ ثبت‌شده نمی‌خواند — یکی سوم می‌گفت و دیگری دوم.'))
    # ── رنگ کارت‌های «ارتباط با ریاست» ──
    # پیش از این پنج رنگ در CSS ثابت بود و عوض‌کردنشان یک دیپلوی
    # می‌خواست. خالی یعنی همان رنگ پیش‌فرض قالب.
    TILE_HELP = _('خالی بگذارید تا رنگ پیش‌فرض بماند.')
    tile_color_phone = models.CharField(
        _('رنگ کارت تلفن'), max_length=9, blank=True, help_text=TILE_HELP)
    tile_color_email = models.CharField(
        _('رنگ کارت ایمیل'), max_length=9, blank=True, help_text=TILE_HELP)
    tile_color_hours = models.CharField(
        _('رنگ کارت روزهای مراجعه'), max_length=9, blank=True, help_text=TILE_HELP)
    tile_color_floor = models.CharField(
        _('رنگ کارت دفتر ریاست'), max_length=9, blank=True, help_text=TILE_HELP)
    tile_color_address = models.CharField(
        _('رنگ کارت نشانی'), max_length=9, blank=True, help_text=TILE_HELP)

    president_cv = models.FileField(
        _('فایل رزومه'), upload_to='presidency/cv/', blank=True, null=True,
        validators=[FileExtensionValidator(
            allowed_extensions=['pdf', 'doc', 'docx'])],
        help_text=_('PDF یا Word. دکمهٔ «رزومه» در صفحهٔ ریاست به همین فایل می‌رود.'))


    class Meta:
        verbose_name = _('دفتر ریاست')
        verbose_name_plural = _('دفتر ریاست')

    def __str__(self):
        return self.president_name or 'دفتر ریاست'

    # ── متن‌های چندخطی به فهرست ──
    # هر سه فیلد در ادمین یک textarea هستند و کاربر خط‌به‌خط می‌نویسد.
    # چاپ‌کردنشان به‌صورت یک پاراگرافِ به‌هم‌چسبیده همان کاری بود که
    # قالب قبلی می‌کرد و خواندنش سخت بود.
    @staticmethod
    def _lines(value: str) -> list:
        return [ln.strip(' 	-•—') for ln in (value or '').splitlines() if ln.strip()]

    @property
    def education_list(self) -> list:
        return self._lines(self.president_education)

    @property
    def resume_list(self) -> list:
        return self._lines(self.president_resume)

    @property
    def research_list(self) -> list:
        return self._lines(self.president_research)

    @property
    def teaching_list(self) -> list:
        return self._lines(self.president_teaching)

    @property
    def awards_list(self) -> list:
        return self._lines(self.president_awards)

    @property
    def memberships_list(self) -> list:
        return self._lines(self.president_memberships)

    @property
    def highlight_items(self) -> list:
        """آمار برجسته — هر خط «عدد | برچسب».

        خطی که جداکننده ندارد کنار گذاشته می‌شود، نه اینکه نیمه‌کاره
        رندر شود: یک کارت با عدد خالی بدتر از نبودن کارت است.
        """
        items = []
        for line in self._lines(self.president_highlights):
            if '|' not in line:
                continue
            number, _, label = line.partition('|')
            number, label = number.strip(), label.strip()
            if number and label:
                items.append({'number': number, 'label': label})
        return items

    @property
    def cv_sections(self) -> list:
        """بخش‌های رزومه به همان ترتیبی که روی صفحه می‌آیند.

        قالب به‌جای پنج بلوک تکراری، روی همین فهرست حلقه می‌زند —
        پس اضافه‌کردن بخش تازه یک ردیف اینجاست، نه بیست خط HTML.
        `tone` شمارهٔ رنگ است؛ سند اصلاحات چندرنگ‌بودن را خواسته.
        """
        raw = [
            ('education', 'سوابق تحصیلی', 'fa-graduation-cap', self.education_list),
            ('resume', 'سوابق اجرایی', 'fa-briefcase', self.resume_list),
            ('teaching', 'سوابق تدریسی', 'fa-chalkboard-teacher', self.teaching_list),
            ('awards', 'جوایز و افتخارات', 'fa-award', self.awards_list),
            ('memberships', 'عضویت‌های علمی', 'fa-users-rectangle', self.memberships_list),
            ('research', 'زمینه‌های پژوهشی', 'fa-flask', self.research_list),
        ]
        sections = []
        for index, (key, title, icon, items) in enumerate(raw, start=1):
            if not items:
                continue
            sections.append({
                'key': key, 'title': title, 'icon': icon,
                'items': items, 'tone': index,
            })
        return sections

    @property
    def website_label(self) -> str:
        """عنوان دکمهٔ وب‌سایت — اگر خالی بود، نام دامنه."""
        if self.president_website_label:
            return self.president_website_label
        host = (self.president_website or '').split('//')[-1]
        return host.split('/')[0] or ''

    @property
    def tile_styles(self) -> dict:
        """رنگ کارت‌های ارتباط، فقط مقدارهای معتبر.

        این مقدارها داخل صفت style کارت می‌نشینند؛ هر رشتهٔ دیگری
        آنجا می‌تواند از اعلان بیرون بزند، پس هرچه شکل هگز نداشته
        باشد دور ریخته می‌شود — نه پاک‌سازی، نه فرار دادن.
        """
        import re

        pattern = re.compile(
            r'^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$')
        found = {}
        for key in ('phone', 'email', 'hours', 'floor', 'address'):
            value = (getattr(self, 'tile_color_%s' % key, '') or '').strip()
            if pattern.match(value):
                found[key] = '--tile:%s' % value
        return found

    @property
    def orcid_url(self) -> str:
        return 'https://orcid.org/%s' % self.president_orcid if self.president_orcid else ''

    @property
    def photo_size(self) -> tuple | None:
        """ابعاد واقعی عکس رئیس، برای گذاشتن در width/height تگ img.

        عکس تمام‌عرض است و ارتفاعش از نسبت خودش می‌آید؛ بدون این دو
        عدد، مرورگر تا رسیدن فایل ارتفاع را نمی‌داند و کل صفحه پس از
        بارگذاری یک تکان می‌خورد (layout shift).

        خواندن ابعاد یعنی باز کردن فایل؛ اگر فایل روی دیسک نباشد —
        که بعد از انتقال مدیا پیش می‌آید — نباید کل صفحه بترکد.
        """
        if not self.president_photo:
            return None
        try:
            return (self.president_photo.width, self.president_photo.height)
        except Exception:                      # noqa: BLE001
            return None


class PresidencyOfficeUnit(models.Model):
    """زیرصفحه‌های دفتر ریاست مطابق سایت رسمی.

    مدل قبلی فقط عنوان و یک متن داشت، پس صفحهٔ هر واحد یک پاراگراف
    تنها بود. چیزی که مراجعه‌کننده واقعاً دنبالش است — مسئول واحد،
    شمارهٔ داخلی و شرح وظایف — اصلاً جایی برای ذخیره نداشت.
    """
    slug = models.SlugField(_('اسلاگ'), max_length=80, unique=True, allow_unicode=True)
    title = models.CharField(_('عنوان'), max_length=200)
    icon = models.CharField(
        _('آیکون'), max_length=60, default='fa-building',
        help_text=_('کلاس Font Awesome، مثلاً fa-user-tie'),
    )
    content = models.TextField(_('محتوا'), blank=True)

    # ── مسئول واحد ──
    manager_name = models.CharField(_('نام مسئول'), max_length=200, blank=True)
    manager_title = models.CharField(_('سمت مسئول'), max_length=200, blank=True)
    manager_photo = models.ImageField(
        _('تصویر مسئول'), upload_to='presidency/units/', blank=True, null=True)

    # ── تماس ──
    phone = models.CharField(_('تلفن'), max_length=50, blank=True)
    extension = models.CharField(_('شماره داخلی'), max_length=20, blank=True)
    email = models.EmailField(_('ایمیل'), blank=True)
    location = models.CharField(
        _('محل استقرار'), max_length=200, blank=True,
        help_text=_('مثلاً: ساختمان مرکزی، طبقه دوم، اتاق ۲۰۴'))
    office_hours = models.CharField(_('ساعات مراجعه'), max_length=200, blank=True)

    duties = models.TextField(
        _('شرح وظایف'), blank=True,
        help_text=_('هر وظیفه در یک خط جدا بنویسید؛ فهرست‌وار نمایش داده می‌شود.'))

    order = models.PositiveIntegerField(_('ترتیب'), default=0)
    is_active = models.BooleanField(_('فعال'), default=True)

    class Meta:
        verbose_name = _('واحد دفتر ریاست')
        verbose_name_plural = _('واحدهای دفتر ریاست')
        ordering = ['order', 'id']

    def __str__(self):
        return self.title

    @property
    def duty_list(self) -> list:
        """هر خط یک وظیفه — خط‌های خالی نادیده گرفته می‌شوند."""
        return [line.strip(' -•\t') for line in (self.duties or '').splitlines()
                if line.strip(' -•\t')]

    @property
    def contact_line(self) -> str:
        """تلفن + داخلی در یک رشته، برای نمایش فشرده."""
        if self.phone and self.extension:
            return '%s داخلی %s' % (self.phone, self.extension)
        return self.phone or (('داخلی %s' % self.extension) if self.extension else '')


class GraduateStudiesInfo(models.Model):
    """اطلاعات صفحه تحصیلات تکمیلی (تک‌رکوردی)"""
    manager_name = models.CharField(_('مدیر تحصیلات تکمیلی'), max_length=200, blank=True)
    intro = models.TextField(_('معرفی'), blank=True)

    class Meta:
        verbose_name = _('تحصیلات تکمیلی')
        verbose_name_plural = _('تحصیلات تکمیلی')

    def __str__(self):
        return self.manager_name or 'تحصیلات تکمیلی'


class Council(models.Model):
    """شوراها و کمیته‌های موسسه.

    ساختار شوراها از سند رسمی «اعضای شورا»ی موسسه می‌آید — هیات
    رئیسه، شورای دانشگاه، شورای آموزشی و تحصیلات تکمیلی، شورای
    پژوهش و فناوری، و شورای دانشجویی و فرهنگی و اجتماعی؛ متن اولیه
    را دستور seed_councils می‌ریزد. مثل بقیهٔ محتوا از پنل قابل
    ویرایش است تا تغییر ترکیب اعضا نیازی به دست‌زدن به کد نداشته باشد.
    """

    name = models.CharField(_('نام شورا'), max_length=200)
    slug = models.SlugField(_('نشانی'), unique=True, allow_unicode=True)
    short_description = models.CharField(
        _('معرفی کوتاه'), max_length=300, blank=True,
        help_text=_('یک جمله؛ زیر نام شورا در فهرست دیده می‌شود.'))
    duties = models.TextField(
        _('شرح وظایف'), blank=True,
        help_text=_('هر وظیفه در یک خط.'))
    members = models.TextField(
        _('اعضا'), blank=True,
        help_text=_('هر عضو در یک خط؛ مثلاً «دکتر … — رئیس شورا».'))
    head = models.CharField(_('رئیس شورا'), max_length=200, blank=True)
    icon = models.CharField(
        _('آیکون'), max_length=50, default='fa-users-rectangle',
        help_text=_('نام آیکون Font Awesome، بدون پیشوند fas.'))
    order = models.PositiveIntegerField(_('ترتیب'), default=0)
    is_active = models.BooleanField(_('فعال'), default=True)

    class Meta:
        verbose_name = _('شورا')
        verbose_name_plural = _('شوراها')
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse('core:council_detail', args=[self.slug])

    @property
    def duty_list(self) -> list:
        return [line.strip() for line in self.duties.splitlines()
                if line.strip()]

    @property
    def member_list(self) -> list:
        return [line.strip() for line in self.members.splitlines()
                if line.strip()]


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
        ('academic', _('آموزش')),
        ('research', _('پژوهش')),
        ('welfare', _('فرهنگی دانشجویی')),
        ('graduate', _('تحصیلات تکمیلی')),
    ]
    DEGREE_LEVEL_CHOICES = [
        ('general', _('عمومی (بدون پوشه مقطع)')),
        ('associate_cont', _('کاردانی پیوسته')),
        ('bachelor_discontinuous', _('کارشناسی ناپیوسته')),
        ('bachelor_continuous', _('کارشناسی پیوسته')),
        ('associate_tech', _('کاردانی فنی')),
        ('master', _('کارشناسی ارشد')),
        # قدیمی
        ('associate', _('کاردانی ناپیوسته')),
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
    def has_file(self) -> bool:
        """PDF واقعاً روی سرور هست؟

        نام فایل در دیتابیس بودن کافی نیست — ده‌ها سند روی سایت زنده
        نام داشتند و فایلشان نبود، و دکمهٔ دانلودشان به ۴۰۴ می‌رسید.
        """
        return file_present(self.file)

    @property
    def has_word(self) -> bool:
        return file_present(self.word_file)

    @property
    def download_url(self):
        # فایلی که روی دیسک نیست، نشانی دانلود هم ندارد؛ اگر لینک
        # بیرونی داشته باشد، همان بهتر از یک ۴۰۴ است.
        if self.has_file:
            return self.file.url
        return self.external_url or ''

    @classmethod
    def degree_folder_meta(cls):
        """پوشه‌های مقطع برای نمایش در سایت (به‌ترتیب رسمی)."""
        icons = {
            'associate_cont': 'fas fa-certificate',
            'bachelor_discontinuous': 'fas fa-book-reader',
            'bachelor_continuous': 'fas fa-graduation-cap',
            'associate_tech': 'fas fa-cogs',
            'master': 'fas fa-user-graduate',
            'associate': 'fas fa-folder',
            'general': 'fas fa-folder-open',
        }
        order = [
            'associate_cont',
            'bachelor_discontinuous',
            'bachelor_continuous',
            'associate_tech',
            'master',
            'associate',
            'general',
        ]
        label_map = dict(cls.DEGREE_LEVEL_CHOICES)
        folders = []
        for key in order:
            if key not in label_map:
                continue
            folders.append({
                'key': key,
                'label': label_map[key],
                'icon': icons.get(key, 'fas fa-folder'),
            })
        return folders


class HomeFeature(models.Model):
    """مزیت تحصیل در موسسه — بخش «مزایا» در صفحهٔ اصلی.

    تا پیش از این شش کارت این بخش کاملاً در قالب هاردکد بود و تغییر متن
    یا آیکونشان به دیپلوی نیاز داشت.
    """
    TONE_CHOICES = [
        ('blue',   'آبی'),
        ('green',  'سبز'),
        ('gold',   'طلایی'),
        ('violet', 'بنفش'),
        ('red',    'قرمز'),
        ('amber',  'کهربایی'),
        ('teal',   'فیروزه‌ای'),
    ]
    # هم‌خانواده با پالت صفحه (main.css) — همه روی زمینهٔ روشن خوانا هستند
    TONE_HEX = {
        'blue': '#2b6ca8', 'green': '#0f9d78', 'gold': '#c9922b',
        'violet': '#6d5bd0', 'red': '#d92d20', 'amber': '#c9922b',
        'teal': '#0d8a8a',
    }

    title = models.CharField(_('عنوان'), max_length=120)
    description = models.CharField(_('توضیح کوتاه'), max_length=250, blank=True)
    icon = models.CharField(
        _('آیکون'), max_length=60, default='fa-star',
        help_text=_('کلاس Font Awesome، مثلاً fa-graduation-cap'),
    )
    tone = models.CharField(_('رنگ آیکون'), max_length=10, choices=TONE_CHOICES, default='blue')
    image = models.ImageField(
        _('تصویر'), upload_to='features/', blank=True, null=True,
        help_text=_('اختیاری — اگر بگذارید جای آیکون نمایش داده می‌شود.'),
    )
    link = models.CharField(_('لینک'), max_length=300, blank=True, default='')
    order = models.PositiveIntegerField(_('ترتیب'), default=0)
    is_active = models.BooleanField(_('فعال'), default=True)

    class Meta:
        verbose_name = _('مزیت تحصیل')
        verbose_name_plural = _('مزایای تحصیل (صفحه اصلی)')
        ordering = ['order', 'id']

    def __str__(self):
        return self.title

    @property
    def color(self) -> str:
        return self.TONE_HEX.get(self.tone, '#1a73e8')


class HomeSection(models.Model):
    """ظاهر هر بخش صفحهٔ اصلی — عنوان، زیرعنوان، تصویر پس‌زمینه.

    هر لایهٔ صفحهٔ اصلی با یک کلید ثابت شناخته می‌شود. اگر رکوردی برای آن
    کلید وجود داشته باشد، عنوان و تصویر پس‌زمینه‌اش از پنل خوانده می‌شود؛
    وگرنه همان متن پیش‌فرض قالب می‌ماند. یعنی افزودن رکورد اختیاری است و
    نبودش چیزی را نمی‌شکند.
    """
    SECTION_CHOICES = [
        ('stats',       'نوار آمار'),
        ('timeline',    'تقویم آموزشی'),
        ('features',    'مزایای تحصیل'),
        ('quicklinks',  'دسترسی سریع'),
        ('news',        'اخبار و اطلاعیه‌ها'),
        ('departments', 'دانشکده‌ها و گروه‌ها'),
        # «هیئت علمی» از صفحهٔ اصلی برداشته شد؛ کلیدش هم اینجا نماند
        # تا مدیر برای بخشی که وجود ندارد تصویر و عنوان نگذارد.
        ('events',      'رویدادها'),
        ('gallery',     'گالری تصاویر'),
        ('alumni',      'فارغ‌التحصیلان'),
        ('faq',         'پرسش‌های متداول'),
        ('cta',         'فراخوان پایانی'),
    ]
    OVERLAY_CHOICES = [
        ('none',  'بدون پوشش'),
        ('light', 'پوشش روشن'),
        ('dark',  'پوشش تیره'),
        ('navy',  'پوشش سرمه‌ای'),
    ]

    key = models.CharField(
        _('بخش'), max_length=30, choices=SECTION_CHOICES, unique=True,
    )
    title = models.CharField(
        _('عنوان'), max_length=200, blank=True,
        help_text=_('خالی = عنوان پیش‌فرض قالب حفظ می‌شود.'),
    )
    subtitle = models.CharField(_('زیرعنوان'), max_length=300, blank=True)
    image = models.ImageField(
        _('تصویر پس‌زمینه'), upload_to='sections/', blank=True, null=True,
    )
    overlay = models.CharField(
        _('پوشش روی تصویر'), max_length=10, choices=OVERLAY_CHOICES, default='light',
        help_text=_('برای خوانا ماندن متن روی تصویر.'),
    )
    is_visible = models.BooleanField(
        _('نمایش این بخش'), default=True,
        help_text=_('برداشتن تیک، کل بخش را از صفحهٔ اصلی حذف می‌کند.'),
    )

    class Meta:
        verbose_name = _('بخش صفحه اصلی')
        verbose_name_plural = _('بخش‌های صفحه اصلی (تصویر و عنوان)')
        ordering = ['key']

    def __str__(self):
        return self.get_key_display()

    @property
    def overlay_css(self) -> str:
        return {
            'none':  'transparent',
            'light': 'rgba(255,255,255,.88)',
            'dark':  'rgba(10,20,30,.72)',
            'navy':  'rgba(6,26,44,.80)',
        }.get(self.overlay, 'rgba(255,255,255,.88)')

    @property
    def is_dark_overlay(self) -> bool:
        """پوشش تیره انتخاب شده و تصویری هم هست؟

        متن بخش‌ها به‌طور پیش‌فرض تیره است. اگر ادمین تصویری با پوشش تیره
        بگذارد، آن متن روی زمینهٔ تیره ناخوانا می‌شود؛ قالب با این پرچم
        کلاس `sec-on-dark` را اضافه می‌کند تا رنگ متن روشن شود.
        """
        return bool(self.image) and self.overlay in ('dark', 'navy')


# صف پیامک — مدل در ماژول جدا نگه داشته شده تا منطق صف کنار خودش
# بماند؛ این ایمپورت لازم است تا اپ آن را ثبت کند.
from core.sms_queue import QueuedSMS  # noqa: E402,F401
