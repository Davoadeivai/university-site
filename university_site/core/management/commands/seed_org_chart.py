"""ساخت چارت سازمانی از روی داده‌هایی که واقعاً در سایت ثبت شده‌اند.

چرا از روی داده و نه از روی یک فهرست ثابت
─────────────────────────────────────────
معاونت‌ها و واحدهای دفتر ریاست از قبل در پایگاه داده هستند. اگر چارت را
با فهرستی جداگانه پر کنیم، دو منبع حقیقت می‌سازیم که بلافاصله از هم
جدا می‌افتند — معاونتی که در پنل حذف شود، در چارت می‌ماند.

پس چارت از همان رکوردها ساخته می‌شود: ریاست در رأس، معاونت‌های فعال در
لایهٔ دوم، و واحدهای دفتر ریاست زیر ریاست. هر بار اجرا، چارت را با
وضعیت فعلی هماهنگ می‌کند.

    python manage.py seed_org_chart
    python manage.py seed_org_chart --rebuild   # حذف و ساخت دوباره
"""
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = 'ساخت چارت سازمانی از معاونت‌ها و واحدهای ثبت‌شده'

    def add_arguments(self, parser):
        parser.add_argument('--rebuild', action='store_true',
                            help='چارت فعلی حذف و از نو ساخته شود')

    @transaction.atomic
    def handle(self, *args, **options):
        from core.models import (
            OrganizationalChart, PresidencyOffice,
            PresidencyOfficeUnit, VicePresidency,
        )

        if options['rebuild']:
            removed = OrganizationalChart.objects.all().delete()[0]
            self.stdout.write(self.style.WARNING('%d گره قبلی حذف شد.' % removed))

        office = PresidencyOffice.objects.first()

        root, created = OrganizationalChart.objects.get_or_create(
            node_type='president', parent=None,
            defaults={'name': 'ریاست موسسه', 'order': 0},
        )
        root.name = 'ریاست موسسه'
        root.title = 'بالاترین مقام اجرایی موسسه'
        if office:
            root.person_name = root.person_name or office.president_name
            root.person_email = root.person_email or office.president_email
            root.person_phone = root.person_phone or office.president_phone
            if not root.person_photo and office.president_photo:
                root.person_photo = office.president_photo
        root.is_active = True
        root.save()
        self.stdout.write('%s ریاست موسسه' % ('+' if created else '~'))

        # ── لایهٔ دوم: معاونت‌ها ──
        made = synced = 0
        for index, vice in enumerate(
                VicePresidency.objects.filter(is_active=True), start=1):
            label = vice.get_vice_type_display()
            node, is_new = OrganizationalChart.objects.get_or_create(
                name=label, parent=root,
                defaults={'node_type': 'vice', 'order': index},
            )
            node.title = 'معاونت'
            node.person_name = node.person_name or vice.full_name
            node.person_email = node.person_email or vice.email
            node.person_phone = node.person_phone or vice.phone
            node.location = node.location or vice.office
            node.description = node.description or (vice.duties or '')[:400]
            if not node.person_photo and vice.photo:
                node.person_photo = vice.photo
            node.order = index
            node.is_active = True
            node.save()
            made += is_new
            synced += (not is_new)
            self.stdout.write('  %s %s' % ('+' if is_new else '~', label))

        # ── واحدهای دفتر ریاست، زیر ریاست ──
        for index, unit in enumerate(
                PresidencyOfficeUnit.objects.filter(is_active=True), start=50):
            node, is_new = OrganizationalChart.objects.get_or_create(
                name=unit.title, parent=root,
                defaults={'node_type': 'office', 'order': index},
            )
            node.title = 'واحد دفتر ریاست'
            node.person_name = node.person_name or unit.manager_name
            node.person_email = node.person_email or unit.email
            node.person_phone = node.person_phone or unit.contact_line
            node.location = node.location or unit.location
            node.description = node.description or (unit.duties or '')[:400]
            node.order = index
            node.is_active = True
            node.save()
            made += is_new
            synced += (not is_new)
            self.stdout.write('  %s %s' % ('+' if is_new else '~', unit.title))

        self.stdout.write(self.style.SUCCESS(
            '\n%d گره جدید، %d گره هماهنگ شد.' % (made, synced)))
        self.stdout.write(
            'ویرایش از پنل: /admin/core/organizationalchart/\n'
            'اجرای دوباره چیزی را که دستی نوشته‌اید بازنویسی نمی‌کند.'
        )
