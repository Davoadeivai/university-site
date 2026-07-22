"""
هم‌سان‌سازی اطلاعات تماس و حساب‌های بانکی با سایت رسمی aab.ac.ir
Run: python manage.py sync_official_contact
"""
from django.core.management.base import BaseCommand

from core.models import BankAccount, SiteSettings

OFFICIAL_ADDRESS = (
    'مازندران - بابلسر - بهنمیر - بلوار امام خمینی (ره) - '
    'گلستان ۱۵ - موسسه آموزش عالی علامه امینی'
)
OFFICIAL_PHONE = '011-35750810 (الی 15)'
OFFICIAL_POSTAL = '4744135161'

BANK_ACCOUNTS = [
    {
        'title': 'شماره حساب موسسه علامه امینی',
        'bank_name': 'بانک ملت',
        'account_number': '1849113/24',
        'account_holder': 'موسسه آموزش عالی علامه امینی',
        'description': 'شماره حساب موسسه جهت واریز شهریه و سایر پرداخت‌ها. برای شهریه از شناسه واریز اختصاصی استفاده کنید.',
        'order': 1,
    },
    {
        'title': 'شماره حساب دانشگاه مازندران جهت فیش واریزی فارغ‌التحصیلی',
        'bank_name': 'بانک ملی',
        'account_number': '2177395006002',
        'account_holder': 'دانشگاه مازندران',
        'description': 'ویژه فیش واریزی فارغ‌التحصیلی',
        'order': 2,
    },
]


class Command(BaseCommand):
    help = 'Sync contact + bank accounts with official aab.ac.ir'

    def handle(self, *args, **options):
        settings_obj, created = SiteSettings.objects.get_or_create(
            pk=1,
            defaults={
                'university_name_fa': 'موسسه آموزش عالی علامه امینی بهنمیر',
                'university_name_en': 'Allameh Amini Higher Education Institute',
            },
        )
        settings_obj.university_name_fa = 'موسسه آموزش عالی علامه امینی بهنمیر'
        settings_obj.university_name_en = 'Allameh Amini Higher Education Institute'
        settings_obj.address = OFFICIAL_ADDRESS
        settings_obj.phone = OFFICIAL_PHONE
        settings_obj.postal_code = '4744135161'
        if settings_obj.email in ('', 'info@university.ac.ir', 'info@example.com'):
            settings_obj.email = ''
        # آمار صفحه اصلی (قابل ویرایش در ادمین؛ پیش‌فرض هم‌راستا با معرفی سایت)
        if not getattr(settings_obj, 'stat_students', None):
            settings_obj.stat_students = 5000
        if not getattr(settings_obj, 'stat_faculty', None):
            settings_obj.stat_faculty = 200
        if not getattr(settings_obj, 'stat_majors', None):
            settings_obj.stat_majors = 50
        if not getattr(settings_obj, 'stat_years', None):
            settings_obj.stat_years = 30
        settings_obj.save()
        self.stdout.write(self.style.SUCCESS(
            f'SiteSettings {"created" if created else "updated"}: address/phone/postal/stats'
        ))


        for spec in BANK_ACCOUNTS:
            obj, was_created = BankAccount.objects.update_or_create(
                account_number=spec['account_number'],
                defaults={
                    'title': spec['title'],
                    'bank_name': spec['bank_name'],
                    'account_holder': spec['account_holder'],
                    'description': spec['description'],
                    'order': spec['order'],
                    'is_active': True,
                },
            )
            action = 'created' if was_created else 'updated'
            self.stdout.write(self.style.SUCCESS(
                f'BankAccount {action}: {obj.bank_name} {obj.account_number}'
            ))

        # غیرفعال کردن حساب‌های نمونه/نامرتبط
        keep = {a['account_number'] for a in BANK_ACCOUNTS}
        deactivated = (
            BankAccount.objects.exclude(account_number__in=keep)
            .filter(is_active=True)
            .update(is_active=False)
        )
        if deactivated:
            self.stdout.write(self.style.WARNING(f'Deactivated other accounts: {deactivated}'))

        self.stdout.write(self.style.SUCCESS('sync_official_contact done.'))
