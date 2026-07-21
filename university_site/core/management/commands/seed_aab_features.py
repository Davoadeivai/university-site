from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from core.models import (
    BankAccount, PaymentIdentifier, DownloadableDocument, Event, SiteSettings,
)


def _sample_pdf(title: str) -> bytes:
    """Minimal valid PDF without external deps."""
    # Keep ASCII title in content stream
    safe = ''.join(c if ord(c) < 128 else '?' for c in title)[:40] or 'Document'
    stream = f'BT /F1 18 Tf 72 720 Td ({safe}) Tj ET'
    parts = [
        b'%PDF-1.4\n',
        b'1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n',
        b'2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n',
        b'3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] '
        b'/Contents 4 0 R /Resources<< /Font<< /F1 5 0 R >> >> >>endobj\n',
        f'4 0 obj<< /Length {len(stream)} >>stream\n{stream}\nendstream\nendobj\n'.encode(),
        b'5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n',
        b'xref\n0 6\n0000000000 65535 f \n',
        b'trailer<< /Size 6 /Root 1 0 R >>\nstartxref\n0\n%%EOF\n',
    ]
    return b''.join(parts)


class Command(BaseCommand):
    help = 'محتوای واقعی‌نما: حساب بانکی، اسناد PDF، لینک سامانه‌ها، رویداد'

    def handle(self, *args, **options):
        settings_obj, _ = SiteSettings.objects.get_or_create(
            pk=1,
            defaults={
                'university_name_fa': 'موسسه آموزش عالی علامه امینی بهنمیر',
                'university_name_en': 'Allameh Amini Higher Education Institute',
            },
        )
        updated = []
        if not settings_obj.external_lms_url:
            settings_obj.external_lms_url = 'http://127.0.0.1:8000/dashboard/'
            updated.append('external_lms_url')
        if not settings_obj.external_admin_url:
            settings_obj.external_admin_url = 'http://127.0.0.1:8000/admin/'
            updated.append('external_admin_url')
        if not settings_obj.phone:
            settings_obj.phone = '011-35750810'
            updated.append('phone')
        if not settings_obj.address:
            settings_obj.address = 'مازندران - بابلسر - بهنمیر - بلوار امام خمینی (ره) - گلستان ۱۵'
            updated.append('address')
        if not settings_obj.postal_code:
            settings_obj.postal_code = '4744135161'
            updated.append('postal_code')
        if updated:
            settings_obj.save(update_fields=updated + (['university_name_fa', 'university_name_en'] if settings_obj.pk else []))
            self.stdout.write(self.style.SUCCESS(f'SiteSettings به‌روز شد: {", ".join(updated)}'))

        if not BankAccount.objects.exists():
            BankAccount.objects.create(
                title='شماره حساب موسسه جهت واریز شهریه',
                bank_name='بانک ملت',
                account_number='1849113/24',
                iban='IR120120000000001849113024',
                account_holder='موسسه آموزش عالی',
                description='برای واریز شهریه حتماً از شناسه واریز اختصاصی استفاده کنید.',
                order=1,
            )
            BankAccount.objects.create(
                title='شماره حساب جهت فیش فارغ‌التحصیلی',
                bank_name='بانک ملی',
                account_number='2177395006002',
                account_holder='موسسه آموزش عالی',
                description='ویژه فیش واریزی فارغ‌التحصیلی',
                order=2,
            )
            self.stdout.write(self.style.SUCCESS('حساب‌های بانکی نمونه اضافه شد.'))

        if not PaymentIdentifier.objects.exists():
            PaymentIdentifier.objects.create(
                full_name='دانشجوی نمونه',
                national_id='0012345678',
                student_number='1400123456',
                payment_id='9912345678901',
                academic_year='1404-1405',
                note='نمونه برای تست جستجو',
            )
            self.stdout.write(self.style.SUCCESS('شناسه واریز نمونه (کد ملی 0012345678) اضافه شد.'))

        docs_spec = [
            ('آیین‌نامه آموزشی', 'regulation', 'آیین‌نامه آموزشی موسسه (نمونه قابل دانلود)'),
            ('فرم درخواست گواهی اشتغال به تحصیل', 'form', 'فرم رسمی امور دانشجویی'),
            ('راهنمای ثبت‌نام آنلاین', 'guide', 'مراحل ثبت‌نام، OTP و پیگیری پذیرش'),
        ]
        for title, category, desc in docs_spec:
            doc, created = DownloadableDocument.objects.get_or_create(
                title=title,
                defaults={'category': category, 'description': desc, 'order': docs_spec.index((title, category, desc)) + 1},
            )
            if created or not doc.file:
                pdf = _sample_pdf(title)
                doc.file.save(f'{category}_{doc.pk or "new"}.pdf', ContentFile(pdf), save=True)
                self.stdout.write(self.style.SUCCESS(f'سند PDF: {title}'))

        today = timezone.now().date()
        if not Event.objects.filter(date__gte=today).exists():
            Event.objects.create(
                title='جلسه توجیهی دانشجویان جدید',
                description='برگزاری جلسه آشنایی با مقررات و خدمات آموزشی موسسه.',
                date=today + timedelta(days=14),
                location='سالن همایش',
                is_featured=True,
            )
            self.stdout.write(self.style.SUCCESS('رویداد نمونه اضافه شد.'))

        self.stdout.write(self.style.SUCCESS('seed_aab_features تمام شد.'))
