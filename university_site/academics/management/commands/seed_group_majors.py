"""
Seed majors for each academic group (from official catalog screenshots).
Run after seed_groups:
  python manage.py seed_group_majors
  python manage.py seed_group_majors --force
"""
import hashlib
import sys
import io
from django.core.management.base import BaseCommand
from academics.models import AcademicGroup, Major, Department

if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


def make_ascii_slug(degree, name, order):
    """Slug فقط با حروف لاتین/عدد تا با URL سازگار باشد."""
    digest = hashlib.md5(f'{degree}|{name}|{order}'.encode('utf-8')).hexdigest()[:10]
    return f'{degree}-{order}-{digest}'


# (group_name_substring, degree_code, major_name, order)
CATALOG = [
    ('معماری', 'bachelor_cont', 'مهندسی معماری', 1),
    ('معماری', 'bachelor_disc', 'مهندسی تکنولوژی معماری', 1),
    ('معماری', 'associate_cont', 'معماری نقشه کشی', 1),
    ('معماری', 'associate_cont', 'نقشه برداری', 2),
    ('معماری', 'associate_cont', 'نقشه کشی و طراحی صنعتی', 3),

    ('کامپیوتر', 'bachelor_cont', 'مهندسی کامپیوتر - نرم افزار', 1),
    ('کامپیوتر', 'bachelor_disc', 'تکنولوژی مهندسی کامپیوتر', 1),
    ('کامپیوتر', 'associate_cont', 'کامپیوتر-نرم افزار', 1),

    ('مکانیک', 'bachelor_disc', 'مهندسی تکنولوژی مکانیک خودرو', 1),
    ('مکانیک', 'associate_disc', 'مکانیک خودرو', 1),

    ('حسابداری', 'master', 'حسابداری - حسابداری', 1),
    ('حسابداری', 'master', 'حسابداری - گرایش حسابرسی', 2),
    ('حسابداری', 'bachelor_cont', 'حسابداری', 1),
    ('حسابداری', 'bachelor_disc', 'حسابداری', 1),
    ('حسابداری', 'associate_disc', 'حسابداری', 1),
    ('حسابداری', 'associate_cont', 'حسابداری و بازرگانی', 1),

    ('مدیریت صنعتی', 'master', 'مدیریت صنعتی - گرایش مدیریت کیفیت و بهره‌وری', 1),
    ('مدیریت صنعتی', 'master', 'مدیریت صنعتی - تولید و عملیات', 2),
    ('مدیریت صنعتی', 'bachelor_disc', 'مدیریت صنعتی', 1),
    ('مدیریت صنعتی', 'bachelor_cont', 'مدیریت مالی', 1),
    ('مدیریت صنعتی', 'associate', 'مدیریت صنعتی', 1),

    ('برق', 'bachelor_cont', 'مهندسی برق', 1),
    ('برق', 'bachelor_disc', 'تکنولوژی مهندسی برق', 1),
    ('برق', 'bachelor_disc', 'تکنولوژی مهندسی مخابرات - انتقال', 2),
    ('برق', 'associate_cont', 'الکتروتکنیک تاسیسات الکتریکی', 1),
    ('برق', 'associate_cont', 'الکتروتکنیک برق صنعتی', 2),
    ('برق', 'associate_cont', 'الکترونیک الکترونیک عمومی', 3),
    ('برق', 'associate_cont', 'الکترونیک الکترونیک دریایی', 4),
    ('برق', 'associate_disc', 'ارتباط داده ها', 1),

    ('بازرگانی', 'master', 'مدیریت بازرگانی - گرایش مدیریت مالی', 1),
    ('بازرگانی', 'master', 'مدیریت بازرگانی - گرایش بازاریابی', 2),
    ('بازرگانی', 'master', 'مدیریت بازرگانی - گرایش بازرگانی بین‌الملل', 3),
    ('بازرگانی', 'bachelor_disc', 'مدیریت بازرگانی', 1),
    ('بازرگانی', 'bachelor_disc', 'مدیریت بیمه', 2),
    ('بازرگانی', 'associate_disc', 'مدیریت بازرگانی', 1),
    ('بازرگانی', 'associate_disc', 'امور دولتی', 2),

    ('علوم اجتماعی', 'bachelor_cont', 'علوم اجتماعی - گرایش پژوهشگری', 1),

    ('روانشناسی', 'bachelor_cont', 'روانشناسی', 1),

    ('علوم تربیتی', 'associate', 'مدیریت آموزشی', 1),
    ('علوم تربیتی', 'associate', 'آموزش و پرورش ابتدایی', 2),
    ('علوم تربیتی', 'master', 'علوم تربیتی - مدیریت آموزشی', 1),
    ('علوم تربیتی', 'master', 'آموزش و پرورش ابتدایی', 2),
]


class Command(BaseCommand):
    help = 'Seed majors per academic group from university catalog'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Recreate majors for matched groups')

    def handle(self, *args, **options):
        force = options['force']
        groups = list(AcademicGroup.objects.select_related('department').all())
        if not groups:
            self.stderr.write(self.style.ERROR('هیچ گروهی نیست. ابتدا seed_groups را اجرا کنید.'))
            return

        created = updated = skipped = 0

        for hint, degree, name, order in CATALOG:
            group = next((g for g in groups if hint in g.name), None)
            if not group:
                self.stdout.write(self.style.WARNING(f'گروه یافت نشد برای: {hint} / {name}'))
                skipped += 1
                continue

            dept = group.department or Department.objects.filter(is_active=True).first()
            if not dept:
                self.stderr.write(self.style.ERROR('دانشکده‌ای وجود ندارد.'))
                return

            slug = make_ascii_slug(degree, name, order)
            base = slug
            n = 1
            while Major.objects.filter(slug=slug).exclude(
                name=name, group=group, degree=degree
            ).exists():
                slug = f'{base}-{n}'
                n += 1

            existing = Major.objects.filter(group=group, name=name, degree=degree).first()
            if existing and not force:
                if not existing.slug.isascii():
                    existing.slug = slug
                    existing.save(update_fields=['slug'])
                    updated += 1
                else:
                    skipped += 1
                continue

            defaults = {
                'department': dept,
                'group': group,
                'slug': slug,
                'order': order,
                'is_active': True,
            }
            if existing and force:
                for k, v in defaults.items():
                    setattr(existing, k, v)
                existing.save()
                updated += 1
            else:
                Major.objects.create(name=name, degree=degree, **defaults)
                created += 1

        fixed = 0
        for m in Major.objects.all():
            if not m.slug.isascii():
                new_slug = make_ascii_slug(m.degree, m.name, m.order or m.pk)
                base = new_slug
                n = 1
                while Major.objects.filter(slug=new_slug).exclude(pk=m.pk).exists():
                    new_slug = f'{base}-{n}'
                    n += 1
                m.slug = new_slug
                m.save(update_fields=['slug'])
                fixed += 1

        self.stdout.write(self.style.SUCCESS(
            f'تمام شد — ایجاد: {created} | بروزرسانی: {updated} | ردشده: {skipped} | اصلاح اسلاگ: {fixed}'
        ))
