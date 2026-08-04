"""گزارش کمبودهای محتوایی صفحات معرفی.

صفحهٔ خالی خطا نمی‌دهد؛ فقط خالی است. این دستور می‌گوید کدام صفحه چقدر
پر شده و دقیقاً چه چیزی کم دارد — تا پیش از اینکه بازدیدکننده به یک
صفحهٔ سفید برسد، خودمان بدانیم.

    python manage.py content_gaps
"""
from django.core.management.base import BaseCommand

from core.completeness import PROFILES, evaluate

# صفحه‌هایی که هیچ رکوردی نداشته باشند، اصلاً رندر نمی‌شوند
EMPTY_PAGE_WARNINGS = {
    'core.PresidencyOffice': 'صفحهٔ «ریاست موسسه» بدون این رکورد خالی است',
    'core.VicePresidency': 'صفحهٔ «معاونت‌ها» بدون رکورد خالی است',
    'core.BoardMember': 'صفحات «هیات موسس» و «هیات امنا» خالی می‌مانند',
    'core.InstitutionGoal': 'صفحهٔ «اهداف موسسه» خالی می‌ماند',
    'core.OrganizationalChart': 'چارت سازمانی خالی می‌ماند',
}


class Command(BaseCommand):
    help = 'گزارش درصد تکمیل و فیلدهای جامانده در صفحات معرفی'

    def handle(self, *args, **options):
        from django.apps import apps

        overall = []

        for label in PROFILES:
            try:
                model = apps.get_model(label)
            except LookupError:
                continue

            name = str(model._meta.verbose_name_plural)
            rows = list(model.objects.all())

            self.stdout.write(self.style.MIGRATE_HEADING('\n%s' % name))

            if not rows:
                warn = EMPTY_PAGE_WARNINGS.get(label, 'هیچ رکوردی ثبت نشده')
                self.stdout.write(self.style.ERROR('  ! %s' % warn))
                overall.append(0)
                continue

            for obj in rows:
                data = evaluate(obj)
                percent = data['percent']
                overall.append(percent)
                style = (self.style.SUCCESS if percent >= 85
                         else self.style.WARNING if percent >= 55
                         else self.style.ERROR)
                self.stdout.write(style('  %3d%%  %s' % (percent, str(obj)[:52])))
                if data['critical']:
                    self.stdout.write('        مهم و خالی: %s'
                                      % '، '.join(data['critical']))
                elif data['missing']:
                    self.stdout.write('        خالی: %s'
                                      % '، '.join(data['missing'][:6]))

        if overall:
            avg = int(round(sum(overall) / len(overall)))
            self.stdout.write('\n' + '─' * 52)
            self.stdout.write('میانگین تکمیل صفحات معرفی: %d%%' % avg)
            self.stdout.write(
                'هر مورد را از پنل ادمین کامل کنید؛ ستون «تکمیل صفحه» '
                'همان‌جا هم نشان داده می‌شود.'
            )
