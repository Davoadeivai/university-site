"""
هم‌سان‌سازی خدمات الکترونیکی و دسترسی سریع با سایت رسمی aab.ac.ir
و پاک‌سازی محتوای دمو.
Run: python manage.py sync_official_eservices
"""
from django.core.management.base import BaseCommand
from django.db.models import Q

from academics.models import AcademicGroup, Department
from core.models import QuickLink, SiteSettings

SAMAWEB = 'http://2.181.0.151/samaweb/'

ESERVICES = [
    {
        'title': 'سامانه خدمات آموزشی',
        'icon': 'fas fa-graduation-cap',
        'url': SAMAWEB,
        'order': 1,
        'open_in_new_tab': True,
    },
    {
        'title': 'سامانه اتوماسیون اداری',
        'icon': 'fas fa-network-wired',
        'url': SAMAWEB,
        'order': 2,
        'open_in_new_tab': True,
    },
    {
        'title': 'کتابخانه دیجیتال',
        'icon': 'fas fa-book',
        'url': '/کتابخانه/',
        'order': 3,
        'open_in_new_tab': False,
    },
    {
        'title': 'آیین نامه ها و فرمها',
        'icon': 'fas fa-file-alt',
        'url': '/آیین-نامه-ها-و-فرم-ها/',
        'order': 4,
        'open_in_new_tab': False,
    },
    {
        'title': 'سامانه نشریات',
        'icon': 'fas fa-newspaper',
        'url': '/پژوهش/مجلات/',
        'order': 5,
        'open_in_new_tab': False,
    },
]

QUICK_ACCESS = [
    ('دفتر مقام معظم رهبری', 'http://www.leader.ir/langs/fa', 1),
    ('پایگاه اینترنتی ریاست جمهوری', 'http://www.president.ir/fa', 2),
    ('وزارت علوم تحقیقات و فناوری', 'http://www.msrt.ir/fa/pages/Home.aspx', 3),
    ('سامانه صندوق رفاه دانشجویی', 'http://www.srd.ir/', 4),
    ('سازمان سنجش آموزش کشور', 'http://www.sanjesh.org', 5),
    ('مرکز جذب اعضای هیأت علمی', 'http://www.mjazb.ir', 6),
    ('سامانه ERP', 'https://erp.msrt.ir/SubSystem/Edari/PRelate/Site/Login.aspx?iftc=1', 7),
]

HOME_LINKS = [
    ('سامانه خدمات آموزشی', 'fas fa-graduation-cap', SAMAWEB, 1, True),
    ('اتوماسیون اداری', 'fas fa-network-wired', SAMAWEB, 2, True),
    ('کتابخانه دیجیتال', 'fas fa-book', '/کتابخانه/', 3, False),
    ('آیین نامه ها و فرمها', 'fas fa-file-alt', '/آیین-نامه-ها-و-فرم-ها/', 4, False),
    ('سامانه نشریات', 'fas fa-newspaper', '/پژوهش/مجلات/', 5, False),
    ('شناسه واریز شهریه', 'fas fa-university', '/شناسه-واریز/', 6, False),
    ('پذیرش دانشجو', 'fas fa-user-plus', '/پذیرش/', 7, False),
    ('همه خدمات', 'fas fa-globe', '/خدمات-الکترونیکی/', 8, False),
]


class Command(BaseCommand):
    help = 'Sync e-services + quick access with official aab.ac.ir; clean demo data'

    def handle(self, *args, **options):
        settings_obj, _ = SiteSettings.objects.get_or_create(pk=1)
        settings_obj.university_name_fa = 'موسسه آموزش عالی علامه امینی بهنمیر'
        if settings_obj.university_name_en in ('', 'Jame University', 'University'):
            settings_obj.university_name_en = 'Allameh Amini Higher Education Institute'
        settings_obj.external_lms_url = SAMAWEB
        settings_obj.external_admin_url = SAMAWEB
        settings_obj.external_publications_url = ''  # internal journals page
        settings_obj.save()
        self.stdout.write(self.style.SUCCESS('SiteSettings external URLs updated'))

        # حذف لینک‌های قدیمی اتوماسیون تغذیه/خوابگاه (اگر مانده باشند)
        removed = QuickLink.objects.filter(
            Q(title__icontains='اتوماسیون تغذیه')
            | Q(title__icontains='اتوماسیون خوابگاه')
            | Q(title__iexact='تغذیه')
            | Q(title__iexact='خوابگاه')
        ).delete()
        self.stdout.write(f'Removed food/dorm automation links: {removed[0]}')

        # پاک‌سازی لینک‌های قبلی این دسته‌ها و seed مجدد
        QuickLink.objects.filter(category__in=['eservice', 'quick_access', 'home']).delete()

        for spec in ESERVICES:
            QuickLink.objects.create(
                title=spec['title'],
                icon=spec['icon'],
                url=spec['url'],
                category='eservice',
                order=spec['order'],
                open_in_new_tab=spec['open_in_new_tab'],
                is_active=True,
            )
        self.stdout.write(self.style.SUCCESS(f'E-services seeded ({len(ESERVICES)})'))

        for title, url, order in QUICK_ACCESS:
            QuickLink.objects.create(
                title=title,
                icon='fas fa-external-link-alt',
                url=url,
                category='quick_access',
                order=order,
                open_in_new_tab=True,
                is_active=True,
            )
        self.stdout.write(self.style.SUCCESS(f'Quick access seeded ({len(QUICK_ACCESS)})'))

        for title, icon, url, order, new_tab in HOME_LINKS:
            QuickLink.objects.create(
                title=title,
                icon=icon,
                url=url,
                category='home',
                order=order,
                open_in_new_tab=new_tab,
                is_active=True,
            )
        self.stdout.write(self.style.SUCCESS(f'Home quick links seeded ({len(HOME_LINKS)})'))

        # مرحله ۱۰ — پاک‌سازی دمو: دپارتمان/گروه bargh
        bargh_groups = AcademicGroup.objects.filter(slug='bargh') | AcademicGroup.objects.filter(name__iexact='bargh')
        for g in bargh_groups:
            g.is_active = False
            g.save(update_fields=['is_active'])
            self.stdout.write(f'  deactivated group: {g.slug}')

        bargh_depts = Department.objects.filter(name__iexact='bargh') | Department.objects.filter(slug='bargh')
        for d in bargh_depts.distinct():
            if hasattr(d, 'is_active'):
                d.is_active = False
                d.save(update_fields=['is_active'])
                self.stdout.write(f'  deactivated dept: {d.name}')
            else:
                self.stdout.write(f'  demo dept present: {d.name} (no is_active field)')

        self.stdout.write(self.style.SUCCESS('Demo cleanup done'))
