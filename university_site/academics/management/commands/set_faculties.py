"""سه دانشکده می‌سازد و یازده گروه را زیرشان می‌چیند.

    python manage.py set_faculties
    python manage.py set_faculties --dry-run
    python manage.py set_faculties --list

چرا لازم شد
───────────
در دیتابیس دو «دانشکده» بود: یکی به نام `bargh` — نامی آزمایشی که
جا مانده بود، بدون هیچ گروه و رشته — و دیگری «تحصیلات تکمیلی» که
هر یازده گروه زیرش جمع شده بودند. «تحصیلات تکمیلی» یک مقطع است،
نه دانشکده؛ پس عملاً ساختار دانشکده‌ای وجود نداشت.

چیدمان زیر از روی همان گروه‌هایی است که موسسه واقعاً دارد، نه از
روی الگوی دانشگاهی دیگری: مهندسی، مدیریت و حسابداری، و علوم
انسانی. همان سه حوزه‌ای که یازده گروه در آن‌ها می‌گنجند.

دستور بارها قابل اجراست: دانشکدهٔ موجود را دوباره نمی‌سازد و
گروهی را که ادمین دستی جابه‌جا کرده، جز با ‎--force‎ برنمی‌گرداند.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from academics.models import AcademicGroup, Department

# (اسلاگ، نام، ترتیب، معرفی کوتاه، کلیدواژه‌های گروه‌ها)
FACULTIES = [
    (
        'fanni-mohandesi', 'دانشکده فنی و مهندسی', 1,
        'گروه‌های مهندسی موسسه — از برق و کامپیوتر تا مکانیک و معماری.',
        ['برق', 'کامپیوتر', 'مکانیک', 'معماری'],
    ),
    (
        'modiriat-hesabdari', 'دانشکده مدیریت و حسابداری', 2,
        'مدیریت صنعتی، بازرگانی و حسابداری — حوزه‌ای که ریاست موسسه '
        'خود از آن برخاسته است.',
        ['حسابداری', 'مدیریتصنعتی', 'مدیریتبازرگانی'],
    ),
    (
        'olum-ensani', 'دانشکده علوم انسانی', 3,
        'علوم اجتماعی، روان‌شناسی، علوم تربیتی و علوم پایه و معارف.',
        ['علوماجتماعی', 'روانشناسی', 'علومتربیتی', 'علومپایه'],
    ),
]

# ردیف‌هایی که دانشکده نیستند و باید برداشته شوند
PLACEHOLDERS = ['bargh', 'تحصیلات تکمیلی']


def key(text: str) -> str:
    """کلید مقایسه — فاصله، نیم‌فاصله و شکل حروف را نادیده می‌گیرد."""
    cleaned = (text or '').replace('ي', 'ی').replace('ك', 'ک')
    cleaned = cleaned.replace('‌', '').replace('‏', '').replace('-', '')
    for word in ('گروه', 'آموزشی', 'دانشکده'):
        cleaned = cleaned.replace(word, '')
    return ''.join(cleaned.split())


class Command(BaseCommand):
    help = 'ساخت دانشکده‌ها و چیدن گروه‌ها زیرشان'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='فقط بگو چه می‌شود، چیزی را عوض نکن')
        parser.add_argument('--list', action='store_true',
                            help='وضعیت فعلی را نشان بده')
        parser.add_argument('--force', action='store_true',
                            help='گروه‌هایی که ادمین جابه‌جا کرده را هم برگردان')

    def handle(self, *args, **options):
        if options['list']:
            self._show()
            return

        dry = options['dry_run']
        groups = list(AcademicGroup.objects.all())
        if not groups:
            self.stdout.write(self.style.WARNING(
                'هیچ گروهی ثبت نشده — چیزی برای چیدن نیست.'))
            return

        with transaction.atomic():
            faculties = self._ensure(dry)
            moved = self._assign(groups, faculties, options['force'], dry)
            majors = self._follow_groups(dry)
            removed = self._drop_placeholders(dry)
            if dry:
                transaction.set_rollback(True)

        head = 'اگر اجرا شود:' if dry else 'انجام شد:'
        self.stdout.write(self.style.SUCCESS(head))
        self.stdout.write('  %d دانشکده' % len(faculties))
        self.stdout.write('  %d گروه جابه‌جا شد' % moved)
        self.stdout.write('  %d رشته دانشکدهٔ گروهش را گرفت' % majors)
        if removed:
            self.stdout.write('  برداشته شد: %s' % '، '.join(removed))
        if dry:
            self.stdout.write('')
            self.stdout.write('(‎--dry-run‎ بود؛ دیتابیس دست‌نخورده ماند.)')

    # ── مراحل ────────────────────────────────────────────────────
    def _ensure(self, dry: bool) -> dict:
        found = {}
        for slug, name, order, blurb, _keys in FACULTIES:
            existing = Department.objects.filter(slug=slug).first()
            if existing:
                found[slug] = existing
                continue
            department = Department(
                slug=slug, name=name, order=order,
                short_description=blurb, is_active=True)
            if not dry:
                department.save()
            else:
                # در dry-run هم باید کلید بخورد تا تخصیص شبیه‌سازی شود
                department.save()
            found[slug] = department
            self.stdout.write('  + %s' % name)
        return found

    def _assign(self, groups, faculties, force: bool, dry: bool) -> int:
        # کلید گروه → اسلاگ دانشکده
        wanted = {}
        for slug, _name, _order, _blurb, keys in FACULTIES:
            for needle in keys:
                wanted[needle] = slug

        placeholder_ids = {
            d.id for d in Department.objects.all()
            if key(d.name) in {key(p) for p in PLACEHOLDERS}
        }

        moved = 0
        for group in groups:
            target = None
            group_key = key(group.name)
            for needle, slug in wanted.items():
                if needle in group_key:
                    target = faculties[slug]
                    break
            if target is None:
                self.stdout.write(self.style.WARNING(
                    '  ? %s — به هیچ دانشکده‌ای نخورد' % group.name))
                continue
            if group.department_id == target.id:
                continue
            # گروهی که ادمین جای دیگری برده، جز با --force دست نمی‌خورد
            settled = (group.department_id
                       and group.department_id not in placeholder_ids)
            if settled and not force:
                continue
            group.department = target
            if not dry:
                group.save(update_fields=['department'])
            moved += 1
            self.stdout.write('  → %s ← %s' % (target.name, group.name))
        return moved

    def _follow_groups(self, dry: bool) -> int:
        """رشته باید دانشکدهٔ گروه خودش را داشته باشد.

        رشته دو رابطه دارد — گروه و دانشکده — و این دو می‌توانند از
        هم جدا بیفتند. همه زیر «تحصیلات تکمیلی» مانده بودند در حالی
        که گروهشان به دانشکدهٔ درست منتقل شده بود؛ نتیجه‌اش دانشکده‌ای
        بدون رشته و یک ردیف جای‌نگهدار پر از رشته بود.
        """
        from academics.models import Major

        changed = 0
        for major in Major.objects.select_related('group').all():
            if major.group is None or major.group.department_id is None:
                continue
            if major.department_id == major.group.department_id:
                continue
            major.department_id = major.group.department_id
            if not dry:
                major.save(update_fields=['department'])
            changed += 1
        return changed

    def _drop_placeholders(self, dry: bool) -> list:
        names = {key(p) for p in PLACEHOLDERS}
        removed = []
        for department in Department.objects.all():
            if key(department.name) not in names:
                continue
            if department.groups.exists() or department.majors.exists():
                self.stdout.write(self.style.WARNING(
                    '  ! %s هنوز محتوا دارد — برداشته نشد.'
                    % department.name))
                continue
            removed.append(department.name)
            if not dry:
                department.delete()
        return removed

    def _show(self):
        self.stdout.write('دانشکده‌ها:')
        for department in Department.objects.order_by('order', 'name'):
            self.stdout.write('  %-30s %d گروه، %d رشته' % (
                department.name,
                department.groups.count(),
                department.majors.count()))
        orphans = AcademicGroup.objects.filter(department__isnull=True)
        if orphans.exists():
            self.stdout.write('بدون دانشکده: %s' % '، '.join(
                orphans.values_list('name', flat=True)))
