from django import forms
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from core.admin_jalali import JalaliAdminMixin
from core.admin_completeness import CompletenessAdminMixin
from core.jalali import format_jalali_date, format_jalali_datetime

# ثبت لاگ فعالیت ادمین (LogEntry) — فقط‌خواندنی، مخصوص superuser
from core import admin_logentry  # noqa: F401
from .models import (
    SiteSettings, Slider, QuickLink, Event, FAQ, PageView,
    InstitutionGoal, BoardMember, CityInfo, CityAttraction,
    PresidencyOffice, PresidencyOfficeUnit, DeputyVice,
    InternationalOffice, InternationalActivity,
    PublicRelations, PressRelease,
    SecurityOffice,
    VicePresidency, ViceUnit, ViceAchievement,
    OrganizationalChart,
    BankAccount, PaymentIdentifier, DownloadableDocument,
    GraduateStudiesInfo,
    HomeFeature, HomeSection,
)
from core.sms_queue import QueuedSMS


@admin.register(SiteSettings)
class SiteSettingsAdmin(CompletenessAdminMixin, admin.ModelAdmin):
    list_display = ['university_name_fa', 'phone', 'email', 'completeness']


    # ── پیش‌نمایش سه فیلد تصویری ──
    # هر سه «یک عکس» می‌خواهند و از روی نامشان معلوم نیست کدام کجا
    # دیده می‌شود؛ یک بار همان عکس در هر سه نشست. پیش‌نمایش کنار هر
    # فیلد، همان لحظه نشان می‌دهد کدام چیست و چه ابعادی دارد.
    LOGO_FIELDS = {
        'logo': ('لوگو', 'فوتر و صفحه‌های چاپی', 'افقی، حدود ۴۰۰ پیکسل'),
        'favicon': ('فاویکون', 'آیکون تب مرورگر', 'مربع، ۳۲ یا ۶۴ پیکسل'),
        'world_class_logo': ('نشان کلاس جهانی',
                             'دو سوی نام در سربرگ، و صفحهٔ ریاست',
                             'مربع، ترجیحاً PNG شفاف'),
    }

    def _preview(self, field_name):
        """تصویر کوچک + ابعاد واقعی + هشدار اگر نسبتش نامناسب باشد."""
        image = getattr(self.instance_for_preview, field_name, None) \
            if getattr(self, 'instance_for_preview', None) else None
        if not image:
            return format_html('<span style="color:#888;">— آپلود نشده —</span>')

        label, where, wanted = self.LOGO_FIELDS[field_name]
        try:
            width, height = image.width, image.height
        except Exception:                      # noqa: BLE001
            # فایل روی دیسک نیست — بعد از انتقال مدیا پیش می‌آید
            return format_html(
                '<span style="color:#b45309;">فایل پیدا نشد: {}</span>', image.name)

        note = ''
        if field_name in ('favicon', 'world_class_logo') and width and height:
            ratio = max(width, height) / min(width, height)
            if ratio > 1.2:
                note = format_html(
                    '<div style="color:#b45309;margin-top:4px;">'
                    'این تصویر مربع نیست ({}×{}). گوشه‌هایش بریده '
                    'می‌شود — بهتر است نسخهٔ مربع بگذارید.</div>',
                    width, height)

        return format_html(
            '<div style="display:flex;gap:12px;align-items:flex-start;">'
            '<img src="{}" style="width:72px;height:72px;object-fit:contain;'
            'border:1px solid #ddd;border-radius:8px;background:'
            'repeating-conic-gradient(#f0f0f0 0% 25%, #fff 0% 50%) 0 0/12px 12px;">'
            '<div style="font-size:12px;line-height:1.9;">'
            '<b>{}</b> — {}<br>ابعاد فعلی: {}×{} پیکسل<br>'
            '<span style="color:#666;">پیشنهاد: {}</span>{}</div></div>',
            image.url, label, where, width, height, wanted, note)

    def logo_preview(self, obj=None):
        return self._preview('logo')
    logo_preview.short_description = 'پیش‌نمایش لوگو'

    def favicon_preview(self, obj=None):
        return self._preview('favicon')
    favicon_preview.short_description = 'پیش‌نمایش فاویکون'

    def world_class_logo_preview(self, obj=None):
        return self._preview('world_class_logo')
    world_class_logo_preview.short_description = 'پیش‌نمایش نشان کلاس جهانی'

    def get_form(self, request, obj=None, **kwargs):
        # پیش‌نمایش‌ها به رکورد نیاز دارند و متدهای readonly آن را
        # نمی‌گیرند؛ همین‌جا نگهش می‌داریم.
        self.instance_for_preview = obj
        return super().get_form(request, obj, **kwargs)

    def get_readonly_fields(self, request, obj=None):
        base = list(super().get_readonly_fields(request, obj))
        for name in ('logo_preview', 'favicon_preview',
                     'world_class_logo_preview'):
            if name not in base:
                base.append(name)
        return base

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        """انتخابگر رنگ مرورگر به‌جای کادر متنی.

        نوشتن دستیِ کد هگز هم غلط‌پذیر است و هم نتیجه را تا ذخیره‌شدن
        نشان نمی‌دهد.
        """
        if db_field.name.startswith('calendar_ink'):
            kwargs['widget'] = forms.TextInput(attrs={
                'type': 'color',
                'style': 'width:70px;height:38px;padding:2px;',
            })
        return super().formfield_for_dbfield(db_field, request, **kwargs)
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': (
                'university_name_fa', 'university_name_en',
                'logo', 'logo_preview',
                'favicon', 'favicon_preview',
                'world_class_logo', 'world_class_logo_preview',
            ),
            'description': (
                'سه فیلد تصویری سه کار متفاوت دارند و پیش‌نمایش هرکدام '
                'زیرش می‌آید.<br>'
                'برای <b>برداشتن</b> یک تصویر، تیک «Clear» کنار همان '
                'فیلد را بزنید و ذخیره کنید — بقیه دست‌نخورده می‌مانند.'
            ),
        }),
        ('اطلاعات تماس', {
            'fields': ('address', 'phone', 'fax', 'email', 'postal_code')
        }),
        ('آمار صفحه اصلی', {
            'fields': ('stat_students', 'stat_faculty', 'stat_majors', 'stat_years'),
        }),
        ('رنگ متن تقویم آموزشی', {
            'fields': (
                'calendar_ink', 'calendar_ink_soft',
                'calendar_ink_dark', 'calendar_ink_soft_dark',
            ),
            'classes': ('collapse',),
            'description': (
                'رنگ نوشته‌های باکس‌های تقویم در صفحهٔ اصلی. خالی '
                'بگذارید تا رنگ پیش‌فرض قالب بماند.<br>'
                '<b>رنگ خود باکس</b> جای دیگری است: هر مرحله در '
                '«تقویم آموزشی» فیلد «رنگ باکس» خودش را دارد.<br>'
                'رنگ روشن روی زمینهٔ روشن خوانده نمی‌شود — پس از '
                'تغییر، صفحهٔ اصلی را در هر دو حالت روشن و تیره ببینید.'
            ),
        }),
        ('شبکه‌های اجتماعی', {
            'fields': ('telegram', 'instagram', 'twitter', 'linkedin', 'youtube')
        }),
        ('سامانه‌های خارجی', {
            'fields': (
                'external_lms_url', 'external_admin_url',
                'external_publications_url',
            ),
            'description': 'لینک‌های سامانه‌های رسمی (samaweb، اتوماسیون اداری، نشریات و …).',
        }),
        ('محتوای صفحه معرفی', {
            'fields': ('about_short', 'history_text', 'vision_text', 'mission_text', 'values_text')
        }),
        ('چارت سازمانی (صفحه معرفی)', {
            'fields': ('org_chart_file',),
            'description': (
                'فایل چارت را اینجا آپلود کنید (PDF، عکس یا Word). '
                'برای حذف فایل فعلی، تیک «پاک کردن» کنار فیلد را بزنید و ذخیره کنید.'
            ),
        }),
        ('اطلاعات تکمیلی', {
            'fields': ('working_hours', 'map_embed', 'established_year')
        }),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()


@admin.register(Slider)
class SliderAdmin(JalaliAdminMixin, admin.ModelAdmin):
    list_display = ['title', 'badge_text', 'badge_color', 'order', 'is_active', 'created_jalali']
    list_editable = ['order', 'is_active']
    list_filter = ['is_active', 'badge_color']
    search_fields = ['title', 'subtitle', 'badge_text']
    fieldsets = (
        ('تصویر و متن اصلی', {
            'fields': ('title', 'subtitle', 'image', 'order', 'is_active')
        }),
        ('دکمه‌های اقدام', {
            'fields': (('link_text', 'link'), ('btn2_text', 'btn2_url')),
        }),
        ('اعلان / خبر مهم روی تصویر', {
            'description': 'اگر می‌خواهید یک اعلان مهم روی این اسلاید نشان داده شود، فیلدهای زیر را پر کنید.',
            'fields': ('badge_text', 'badge_color', 'badge_icon'),
        }),
    )


@admin.register(QuickLink)
class QuickLinkAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'url', 'order', 'open_in_new_tab', 'is_active']
    list_editable = ['order', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['title', 'url']


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'date_jalali', 'location', 'is_featured', 'is_active']
    list_filter = ['is_featured', 'is_active']
    search_fields = ['title']

    @admin.display(description='تاریخ', ordering='date')
    def date_jalali(self, obj):
        return format_jalali_date(obj.date, 'short')


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ['question', 'category', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['question', 'answer']


@admin.register(PageView)
class PageViewAdmin(admin.ModelAdmin):
    list_display = ['path', 'ip', 'date']
    list_filter = ['date']
    search_fields = ['path', 'ip', 'user_agent']
    readonly_fields = ['path', 'ip', 'date', 'user_agent']


@admin.register(InstitutionGoal)
class InstitutionGoalAdmin(CompletenessAdminMixin, admin.ModelAdmin):
    list_display = ['title', 'goal_type', 'order', 'is_active', 'completeness']
    list_editable = ['order', 'is_active']
    list_filter = ['goal_type', 'is_active']
    search_fields = ['title', 'description']


@admin.register(BoardMember)
class BoardMemberAdmin(CompletenessAdminMixin, admin.ModelAdmin):
    list_display = ['full_name', 'board_type', 'title', 'order', 'is_active', 'completeness']
    list_editable = ['order', 'is_active']
    list_filter = ['board_type', 'is_active']
    search_fields = ['full_name', 'title', 'bio']


@admin.register(CityInfo)
class CityInfoAdmin(admin.ModelAdmin):
    list_display = ['title', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    list_filter = ['is_active']
    search_fields = ['title', 'content']
    fieldsets = (
        (None, {
            'fields': ('title', 'content', 'image', 'icon', 'order', 'is_active'),
            'description': 'بخش‌های معرفی شهر بابلسر که در صفحه «شهر بابلسر» نمایش داده می‌شوند.',
        }),
    )


@admin.register(CityAttraction)
class CityAttractionAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['name', 'description', 'address']
    fieldsets = (
        (None, {
            'fields': (
                'name', 'description', 'image', 'category',
                'address', 'order', 'is_active',
            ),
        }),
    )


# ─── حوزه ریاست ───────────────────────────────────────────────

@admin.register(PresidencyOffice)
class PresidencyOfficeAdmin(CompletenessAdminMixin, admin.ModelAdmin):
    list_display = ['president_name', 'office_manager_name', 'president_phone', 'completeness']
    search_fields = ['president_name', 'president_bio', 'office_manager_name']

    def has_add_permission(self, request):
        """فقط یک «دفتر ریاست» می‌تواند وجود داشته باشد.

        سایت این رکورد را با `.first()` می‌خواند؛ رکورد دوم هرگز دیده
        نمی‌شود ولی ادمین فکر می‌کند ذخیره شده. یک بار همین اتفاق افتاد
        و بیوگرافی رئیس در رکورد نامرئی ماند.
        """
        return not PresidencyOffice.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # حذف تنها رکورد، کل صفحهٔ ریاست را خالی می‌کند
        return False

    fieldsets = (
        ('ریاست موسسه', {
            'fields': (
                'president_name', 'president_title', 'president_photo',
                'president_message', 'president_bio',
            ),
            'description': (
                'تصویر رئیس در صفحهٔ ریاست تمام‌عرض و بزرگ نمایش داده '
                'می‌شود، پس عکس افقی با عرض دست‌کم ۱۶۰۰ پیکسل بگذارید. '
                'عکس عمودی یا کوچک، کشیده و مات دیده می‌شود.'
            ),
        }),
        ('رزومه', {
            'fields': (
                'president_highlights',
                'president_education', 'president_resume',
                'president_teaching', 'president_awards',
                'president_memberships', 'president_research',
            ),
            'description': (
                'در هر سه کادر، <b>هر مورد را در یک خط جدا</b> بنویسید — '
                'صفحه آن‌ها را فهرست‌وار نشان می‌دهد. اگر همه را در یک '
                'پاراگراف بنویسید، همان یک پاراگراف چاپ می‌شود.'
            ),
        }),
        ('تماس و حضور علمی', {
            'fields': (
                'president_email', 'president_phone',
                'president_website', 'president_website_label',
                'president_scholar', 'president_orcid',
                'wcu_title', 'wcu_motto',
            ),
            'description': (
                'نشانی وب‌سایت را کامل با https بنویسید. عنوان اگر خالی '
                'بماند، نام دامنه روی دکمه می‌آید.'
            ),
        }),
        ('دفتر ریاست', {
            'fields': (
                'office_manager_name', 'office_duties',
                'office_address', 'office_phone', 'office_fax',
                'office_email', 'office_hours',
            ),
        }),
    )

    def changelist_view(self, request, extra_context=None):
        from django.shortcuts import redirect
        obj = PresidencyOffice.objects.first()
        if obj is None and self.has_add_permission(request):
            return redirect('admin:core_presidencyoffice_add')
        if obj is not None and PresidencyOffice.objects.count() == 1:
            return redirect('admin:core_presidencyoffice_change', obj.pk)
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(PresidencyOfficeUnit)
class PresidencyOfficeUnitAdmin(CompletenessAdminMixin, admin.ModelAdmin):
    list_display = ['title', 'manager_name', 'contact_line', 'order',
                    'is_active', 'completeness']
    list_editable = ['order', 'is_active']
    list_filter = ['is_active']
    prepopulated_fields = {'slug': ('title',)}
    search_fields = ['title', 'content', 'manager_name', 'duties']
    fieldsets = (
        ('واحد', {
            'fields': ('title', 'slug', 'icon', 'order', 'is_active'),
            'description': (
                'هر واحد یک صفحهٔ جدا در بخش «دفتر ریاست» دارد. '
                'برای افزودن واحد تازه کافی است اینجا یک رکورد بسازید؛ '
                'خودش در منوی صفحهٔ دفتر ریاست ظاهر می‌شود.'
            ),
        }),
        ('مسئول واحد', {
            'fields': ('manager_name', 'manager_title', 'manager_photo'),
        }),
        ('تماس و مراجعه', {
            'fields': ('phone', 'extension', 'email', 'location', 'office_hours'),
            'description': 'مراجعه‌کننده بیش از هر چیز دنبال همین‌هاست.',
        }),
        ('محتوا', {
            'fields': ('content', 'duties'),
            'description': 'شرح وظایف را خط‌به‌خط بنویسید؛ فهرست‌وار نمایش داده می‌شود.',
        }),
    )

    @admin.display(description='تماس')
    def contact_line(self, obj):
        return obj.contact_line or '—'


@admin.register(GraduateStudiesInfo)
class GraduateStudiesInfoAdmin(admin.ModelAdmin):
    list_display = ['manager_name']

    def has_add_permission(self, request):
        return not GraduateStudiesInfo.objects.exists()

    def changelist_view(self, request, extra_context=None):
        from django.shortcuts import redirect
        obj = GraduateStudiesInfo.objects.first()
        if obj is None and self.has_add_permission(request):
            return redirect('admin:core_graduatestudiesinfo_add')
        if obj is not None and GraduateStudiesInfo.objects.count() == 1:
            return redirect('admin:core_graduatestudiesinfo_change', obj.pk)
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(DeputyVice)
class DeputyViceAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'vice_type', 'academic_rank', 'phone', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    list_filter = ['vice_type', 'is_active']
    search_fields = ['full_name', 'bio', 'resume']


@admin.register(InternationalOffice)
class InternationalOfficeAdmin(admin.ModelAdmin):
    list_display = ['manager_name', 'phone', 'email']
    search_fields = ['manager_name', 'description']
    fieldsets = (
        ('معرفی دفتر', {
            'fields': ('description', 'address', 'phone', 'email'),
            'description': 'اطلاعات صفحه «دفتر همکاری‌های علمی و بین‌الملل» در سایت از اینجا مدیریت می‌شود.',
        }),
        ('مدیر دفتر', {
            'fields': ('manager_name', 'manager_photo', 'manager_email', 'manager_phone'),
        }),
    )

    def has_add_permission(self, request):
        return not InternationalOffice.objects.exists()

    def changelist_view(self, request, extra_context=None):
        """اگر هنوز رکوردی نیست، مستقیم به فرم افزودن برو."""
        from django.shortcuts import redirect
        obj = InternationalOffice.objects.first()
        if obj is None and self.has_add_permission(request):
            return redirect('admin:core_internationaloffice_add')
        if obj is not None and InternationalOffice.objects.count() == 1:
            return redirect('admin:core_internationaloffice_change', obj.pk)
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(InternationalActivity)
class InternationalActivityAdmin(admin.ModelAdmin):
    list_display = ['title', 'activity_type', 'partner_institution', 'country', 'date_jalali', 'is_active']
    list_editable = ['is_active']
    list_filter = ['activity_type', 'country', 'is_active']
    search_fields = ['title', 'partner_institution', 'country']

    @admin.display(description='تاریخ', ordering='date')
    def date_jalali(self, obj):
        return format_jalali_date(obj.date, 'short')


@admin.register(PublicRelations)
class PublicRelationsAdmin(admin.ModelAdmin):
    # سینگلتون است و changelist به فرم تغییر ریدایرکت می‌شود؛ فیلتر لیست بی‌معنی است
    list_display = ['manager_name', 'phone', 'email']
    search_fields = ['manager_name', 'description', 'duties', 'manager_bio']
    fieldsets = (
        ('معرفی', {'fields': ('description', 'duties', 'phone', 'email', 'address')}),
        ('مدیر', {
            'fields': (
                'manager_name', 'manager_photo', 'manager_bio',
                'manager_email', 'manager_phone',
            ),
        }),
    )

    def has_add_permission(self, request):
        return not PublicRelations.objects.exists()

    def changelist_view(self, request, extra_context=None):
        from django.shortcuts import redirect
        obj = PublicRelations.objects.first()
        if obj is None and self.has_add_permission(request):
            return redirect('admin:core_publicrelations_add')
        if obj is not None and PublicRelations.objects.count() == 1:
            return redirect('admin:core_publicrelations_change', obj.pk)
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(PressRelease)
class PressReleaseAdmin(JalaliAdminMixin, admin.ModelAdmin):
    list_display = ['title', 'published_jalali', 'is_active']
    list_editable = ['is_active']
    list_filter = ['is_active']
    search_fields = ['title', 'content']


@admin.register(SecurityOffice)
class SecurityOfficeAdmin(admin.ModelAdmin):
    list_display = ['manager_name', 'phone', 'emergency_phone', 'email']
    search_fields = ['manager_name', 'description', 'duties']

    def has_add_permission(self, request):
        return not SecurityOffice.objects.exists()

    def changelist_view(self, request, extra_context=None):
        from django.shortcuts import redirect
        obj = SecurityOffice.objects.first()
        if obj is None and self.has_add_permission(request):
            return redirect('admin:core_securityoffice_add')
        if obj is not None and SecurityOffice.objects.count() == 1:
            return redirect('admin:core_securityoffice_change', obj.pk)
        return super().changelist_view(request, extra_context=extra_context)


# ─── معاونت‌ها ─────────────────────────────────────────────────

class ViceUnitInline(admin.TabularInline):
    model = ViceUnit
    extra = 0
    fields = ['name', 'manager', 'phone', 'order', 'is_active']
    show_change_link = True


class ViceAchievementInline(admin.TabularInline):
    model = ViceAchievement
    extra = 0
    fields = ['title', 'status', 'year', 'is_active', 'order']
    show_change_link = True


@admin.register(VicePresidency)
class VicePresidencyAdmin(CompletenessAdminMixin, admin.ModelAdmin):
    list_display  = ['get_vice_type_display', 'full_name', 'academic_rank', 'phone', 'is_active', 'completeness']
    list_editable = ['is_active']
    list_filter   = ['vice_type', 'is_active']
    search_fields = ['full_name', 'bio', 'resume', 'description', 'achievements']
    inlines       = [ViceUnitInline, ViceAchievementInline]
    fieldsets = (
        ('معاونت', {'fields': ('vice_type', 'is_active')}),
        ('معاون', {
            'fields': (
                'full_name', 'academic_rank', 'photo',
                ('email', 'phone', 'office'),
                'bio', 'education', 'resume', 'message',
            ),
        }),
        ('معرفی معاونت', {'fields': ('description', 'duties', 'goals')}),
        ('یادداشت آزاد', {
            'fields': ('achievements',),
            'description': (
                'متن آزاد. برای <strong>دستاوردهای ساختاریافته</strong> از جدول '
                '«دستاوردهای معاونت» در پایین همین صفحه استفاده کنید تا در سایت '
                'قابل نمایش باشد؛ این کادر فقط یادداشت داخلی است.'
            ),
            'classes': ('collapse',),
        }),
    )

    def get_vice_type_display(self, obj):
        return obj.get_vice_type_display()
    get_vice_type_display.short_description = 'نوع معاونت'


@admin.register(ViceUnit)
class ViceUnitAdmin(admin.ModelAdmin):
    list_display  = ['name', 'vice', 'manager', 'phone', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    list_filter   = ['vice', 'is_active']
    search_fields = ['name', 'manager', 'duties']
    list_select_related = ('vice',)


@admin.register(ViceAchievement)
class ViceAchievementAdmin(admin.ModelAdmin):
    list_display  = ['title', 'vice', 'status', 'year', 'is_active']
    list_editable = ['is_active']
    list_filter   = ['vice', 'is_active']
    search_fields = ['title', 'description']
    list_select_related = ('vice',)


# ─── چارت سازمانی ───────────────────────────────────────────────

class OrganizationalChartInline(admin.TabularInline):
    model = OrganizationalChart
    fk_name = 'parent'
    extra = 0
    fields = ['name', 'node_type', 'person_name', 'order', 'is_active']
    show_change_link = True


@admin.register(OrganizationalChart)
class OrganizationalChartAdmin(CompletenessAdminMixin, admin.ModelAdmin):
    list_display = ['name', 'node_type', 'parent', 'person_name', 'order', 'is_active', 'completeness']
    list_editable = ['order', 'is_active']
    list_filter = ['node_type', 'is_active']
    search_fields = ['name', 'person_name', 'title', 'person_email', 'person_phone']
    list_select_related = ('parent',)
    inlines = [OrganizationalChartInline]
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('parent', 'node_type', 'name', 'order', 'is_active')
        }),
        ('اطلاعات مسئول', {
            'fields': ('person_name', 'person_photo', 'title', 'person_email', 'person_phone')
        }),
        ('اطلاعات تکمیلی', {
            'fields': ('description', 'location', 'staff_count')
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('parent')


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ['title', 'bank_name', 'account_number', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    list_filter = ['is_active', 'bank_name']
    search_fields = ['title', 'bank_name', 'account_number', 'iban']


@admin.register(PaymentIdentifier)
class PaymentIdentifierAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'national_id', 'student_number', 'payment_id', 'academic_year', 'is_active']
    list_filter = ['is_active', 'academic_year']
    search_fields = ['full_name', 'national_id', 'student_number', 'payment_id']
    list_editable = ['is_active']


@admin.register(DownloadableDocument)
class DownloadableDocumentAdmin(JalaliAdminMixin, admin.ModelAdmin):
    # بدون fieldsets جدا — همه فیلدها در یک فرم تا آپلود حتماً دیده شود
    fields = (
        'file',
        'word_file',
        'title',
        'degree_level',
        'category',
        'section',
        'description',
        'external_url',
        'order',
        'is_active',
    )
    list_display = [
        'title', 'degree_level', 'category', 'has_pdf', 'has_word',
        'order', 'is_active', 'created_jalali', 'delete_button',
    ]
    list_filter = ['degree_level', 'category', 'is_active']
    list_editable = ['order', 'is_active']
    search_fields = ['title', 'description']
    actions = ['delete_selected_documents']

    @admin.display(boolean=True, description='PDF')
    def has_pdf(self, obj):
        return bool(obj.file)

    @admin.display(boolean=True, description='Word')
    def has_word(self, obj):
        return bool(obj.word_file)

    @admin.display(description='حذف')
    def delete_button(self, obj):
        url = reverse('admin:core_downloadabledocument_delete', args=[obj.pk])
        return format_html(
            '<a class="btn btn-sm btn-danger" href="{}" title="حذف این سند">حذف</a>',
            url,
        )

    @admin.action(description='حذف اسناد انتخاب‌شده')
    def delete_selected_documents(self, request, queryset):
        from django.contrib.admin.actions import delete_selected
        return delete_selected(self, request, queryset)

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop('delete_selected', None)
        return actions


# ─── مزایای تحصیل و بخش‌های صفحه اصلی ─────────────────────────────

@admin.register(HomeFeature)
class HomeFeatureAdmin(admin.ModelAdmin):
    list_display = ['title', 'icon_preview', 'tone', 'has_image', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    list_filter = ['is_active', 'tone']
    search_fields = ['title', 'description']
    fieldsets = (
        ('محتوا', {
            'fields': ('title', 'description', 'link'),
        }),
        ('ظاهر', {
            'fields': ('icon', 'tone', 'image'),
            'description': (
                'آیکون را از <a href="https://fontawesome.com/search?o=r&m=free" '
                'target="_blank" rel="noopener">فهرست Font Awesome</a> انتخاب کنید '
                '(مثلاً <code>fa-flask</code>). اگر تصویر بگذارید، جای آیکون نمایش داده می‌شود.'
            ),
        }),
        ('نمایش', {'fields': ('order', 'is_active')}),
    )

    @admin.display(description='آیکون')
    def icon_preview(self, obj):
        return format_html(
            '<i class="fas {}" style="font-size:20px;color:{};"></i> <code>{}</code>',
            obj.display_icon if hasattr(obj, 'display_icon') else obj.icon,
            obj.color, obj.icon,
        )

    @admin.display(description='تصویر', boolean=True)
    def has_image(self, obj):
        return bool(obj.image)


@admin.register(HomeSection)
class HomeSectionAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'title', 'has_image', 'overlay', 'is_visible']
    list_editable = ['is_visible']
    list_filter = ['is_visible', 'overlay']
    fieldsets = (
        ('بخش', {
            'fields': ('key', 'is_visible'),
            'description': (
                'برای هر بخش صفحهٔ اصلی یک رکورد بسازید. '
                'اگر رکوردی نسازید، همان متن و ظاهر پیش‌فرض قالب باقی می‌ماند.'
            ),
        }),
        ('متن (اختیاری)', {
            'fields': ('title', 'subtitle'),
            'description': 'خالی بگذارید تا عنوان پیش‌فرض قالب حفظ شود.',
        }),
        ('تصویر پس‌زمینه', {
            'fields': ('image', 'overlay'),
            'description': (
                'تصویر پشت کل بخش نمایش داده می‌شود. '
                '«پوشش» لایه‌ای است که روی تصویر می‌آید تا متن خوانا بماند: '
                'با پوشش روشن متن تیره می‌ماند، و با پوشش تیره یا سرمه‌ای '
                'متن آن بخش خودکار سفید می‌شود. '
                'تصویر افقی و حداقل ۱۹۲۰ پیکسل عرض بهترین نتیجه را می‌دهد.'
            ),
        }),
    )

    def get_queryset(self, request):
        """ردیف‌ها به ترتیب ظاهرشدن در صفحه، نه الفبایی.

        ترتیب الفبایی کلیدها (alumni, cta, departments…) هیچ ربطی به
        چیدمان صفحه ندارد و پیدا کردن بخش را سخت می‌کند.
        """
        from django.db.models import Case, IntegerField, When

        order = Case(
            *[When(key=k, then=i)
              for i, (k, _label) in enumerate(self.model.SECTION_CHOICES)],
            default=99, output_field=IntegerField(),
        )
        return super().get_queryset(request).annotate(_page_order=order).order_by('_page_order')

    @admin.display(description='تصویر', boolean=True)
    def has_image(self, obj):
        return bool(obj.image)


# ─── صف پیامک ────────────────────────────────────────────────────

@admin.register(QueuedSMS)
class QueuedSMSAdmin(admin.ModelAdmin):
    """فقط برای دیدن و پیگیری؛ پیام از اینجا ساخته نمی‌شود."""

    list_display = ['phone', 'preview', 'status', 'attempts',
                    'created_jalali', 'sent_jalali']
    list_filter = ['status', 'created_at']
    search_fields = ['phone', 'message', 'last_error']
    readonly_fields = ['phone', 'message', 'attempts', 'last_error',
                       'created_at', 'sent_at']
    actions = ['requeue']

    def has_add_permission(self, request):
        # پیام‌ها را کد تولید می‌کند، نه ادمین
        return False

    @admin.display(description='زمان ثبت', ordering='created_at')
    def created_jalali(self, obj):
        return format_jalali_datetime(obj.created_at, 'short')

    @admin.display(description='زمان ارسال', ordering='sent_at')
    def sent_jalali(self, obj):
        return format_jalali_datetime(obj.sent_at, 'short') if obj.sent_at else '—'

    @admin.action(description='بازگرداندن به صف')
    def requeue(self, request, queryset):
        """پیام ناموفق را دوباره در صف می‌گذارد.

        شمارندهٔ تلاش صفر می‌شود، وگرنه بلافاصله دوباره «ناموفق» می‌شد.
        """
        n = queryset.filter(status='failed').update(
            status='pending', attempts=0, last_error='')
        self.message_user(request, '%d پیام به صف بازگشت.' % n)
