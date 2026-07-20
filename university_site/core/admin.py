from django.contrib import admin
from .models import (
    SiteSettings, Slider, QuickLink, Event, FAQ, PageView,
    InstitutionGoal, BoardMember, CityInfo, CityAttraction,
    PresidencyOffice, DeputyVice,
    InternationalOffice, InternationalActivity,
    PublicRelations, PressRelease,
    SecurityOffice,
    VicePresidency, ViceUnit, ViceAchievement,
    OrganizationalChart,
)


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ['university_name_fa', 'phone', 'email']
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('university_name_fa', 'university_name_en', 'logo', 'favicon')
        }),
        ('اطلاعات تماس', {
            'fields': ('address', 'phone', 'fax', 'email', 'postal_code')
        }),
        ('شبکه‌های اجتماعی', {
            'fields': ('telegram', 'instagram', 'twitter', 'linkedin', 'youtube')
        }),
        ('محتوای صفحه معرفی', {
            'fields': ('about_short', 'history_text', 'vision_text', 'mission_text', 'values_text')
        }),
        ('اطلاعات تکمیلی', {
            'fields': ('working_hours', 'map_embed', 'established_year')
        }),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()


@admin.register(Slider)
class SliderAdmin(admin.ModelAdmin):
    list_display = ['title', 'badge_text', 'badge_color', 'order', 'is_active', 'created_at']
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
    list_display = ['title', 'url', 'color', 'order', 'is_active']
    list_editable = ['order', 'is_active']


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'date', 'location', 'is_featured', 'is_active']
    list_filter = ['is_featured', 'is_active']
    search_fields = ['title']
    date_hierarchy = 'date'


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
    readonly_fields = ['path', 'ip', 'date', 'user_agent']


@admin.register(InstitutionGoal)
class InstitutionGoalAdmin(admin.ModelAdmin):
    list_display = ['title', 'goal_type', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    list_filter = ['goal_type', 'is_active']
    search_fields = ['title', 'description']


@admin.register(BoardMember)
class BoardMemberAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'board_type', 'title', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    list_filter = ['board_type', 'is_active']
    search_fields = ['full_name', 'title', 'bio']


@admin.register(CityInfo)
class CityInfoAdmin(admin.ModelAdmin):
    list_display = ['title', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    search_fields = ['title', 'content']


@admin.register(CityAttraction)
class CityAttractionAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['name', 'description']


# ─── حوزه ریاست ───────────────────────────────────────────────

@admin.register(PresidencyOffice)
class PresidencyOfficeAdmin(admin.ModelAdmin):
    list_display = ['president_name', 'president_title', 'president_phone', 'office_email']
    search_fields = ['president_name', 'president_bio']

    def has_add_permission(self, request):
        return not PresidencyOffice.objects.exists()


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

    def has_add_permission(self, request):
        return not InternationalOffice.objects.exists()


@admin.register(InternationalActivity)
class InternationalActivityAdmin(admin.ModelAdmin):
    list_display = ['title', 'activity_type', 'partner_institution', 'country', 'date', 'is_active']
    list_editable = ['is_active']
    list_filter = ['activity_type', 'country', 'is_active']
    search_fields = ['title', 'partner_institution', 'country']
    date_hierarchy = 'date'


@admin.register(PublicRelations)
class PublicRelationsAdmin(admin.ModelAdmin):
    list_display = ['manager_name', 'phone', 'email']
    search_fields = ['manager_name', 'description', 'duties']

    def has_add_permission(self, request):
        return not PublicRelations.objects.exists()


@admin.register(PressRelease)
class PressReleaseAdmin(admin.ModelAdmin):
    list_display = ['title', 'published_at', 'is_active']
    list_editable = ['is_active']
    list_filter = ['is_active']
    search_fields = ['title', 'content']
    date_hierarchy = 'published_at'


@admin.register(SecurityOffice)
class SecurityOfficeAdmin(admin.ModelAdmin):
    list_display = ['manager_name', 'phone', 'emergency_phone', 'email']
    search_fields = ['manager_name', 'description', 'duties']

    def has_add_permission(self, request):
        return not SecurityOffice.objects.exists()


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
class VicePresidencyAdmin(admin.ModelAdmin):
    list_display  = ['get_vice_type_display', 'full_name', 'academic_rank', 'phone', 'is_active']
    list_editable = ['is_active']
    list_filter   = ['vice_type', 'is_active']
    search_fields = ['full_name', 'bio', 'resume', 'description']
    inlines       = [ViceUnitInline, ViceAchievementInline]

    def get_vice_type_display(self, obj):
        return obj.get_vice_type_display()
    get_vice_type_display.short_description = 'نوع معاونت'


@admin.register(ViceUnit)
class ViceUnitAdmin(admin.ModelAdmin):
    list_display  = ['name', 'vice', 'manager', 'phone', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    list_filter   = ['vice', 'is_active']
    search_fields = ['name', 'manager', 'duties']


@admin.register(ViceAchievement)
class ViceAchievementAdmin(admin.ModelAdmin):
    list_display  = ['title', 'vice', 'status', 'year', 'is_active']
    list_editable = ['is_active']
    list_filter   = ['vice', 'is_active']
    search_fields = ['title', 'description']


# ─── چارت سازمانی ───────────────────────────────────────────────

class OrganizationalChartInline(admin.TabularInline):
    model = OrganizationalChart
    fk_name = 'parent'
    extra = 0
    fields = ['name', 'node_type', 'person_name', 'order', 'is_active']
    show_change_link = True


@admin.register(OrganizationalChart)
class OrganizationalChartAdmin(admin.ModelAdmin):
    list_display = ['name', 'node_type', 'parent', 'person_name', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    list_filter = ['node_type', 'is_active']
    search_fields = ['name', 'person_name', 'title']
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
