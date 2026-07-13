"""
Management command to seed default academic groups.
Run: python manage.py seed_groups
     python manage.py seed_groups --force   # overwrite existing
"""
import sys
import io
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from academics.models import Department, AcademicGroup


# Force UTF-8 output on Windows terminals
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


DEFAULT_GROUPS = [
    {
        'dept_hints': ['برق', 'فنی', 'مهندسی'],
        'name': 'گروه برق، الکترونیک و مخابرات',
        'description': 'گروه آموزشی برق، الکترونیک و مخابرات با هدف تربیت مهندسان متخصص در حوزه‌های طراحی مدارهای الکترونیکی، سیستم‌های مخابراتی و شبکه‌های ارتباطی فعالیت می‌کند.',
        'goals': 'تربیت مهندسان توانمند در حوزه الکترونیک، قدرت، مخابرات و کنترل با رویکرد کاربردی',
        'research_areas': 'طراحی مدار، پردازش سیگنال، شبکه‌های ارتباطی، سیستم‌های هوشمند',
        'order': 1,
    },
    {
        'dept_hints': ['کامپیوتر', 'فنی', 'مهندسی'],
        'name': 'گروه کامپیوتر',
        'description': 'گروه کامپیوتر با تمرکز بر علوم کامپیوتر، مهندسی نرم‌افزار، هوش مصنوعی و شبکه‌های کامپیوتری، دانشجویان را برای ورود به بازار کار فناوری اطلاعات آماده می‌کند.',
        'goals': 'تربیت برنامه‌نویسان و متخصصان IT با تسلط بر فناوری‌های روز دنیا',
        'research_areas': 'هوش مصنوعی، یادگیری ماشین، امنیت شبکه، توسعه نرم‌افزار',
        'order': 2,
    },
    {
        'dept_hints': ['معماری', 'هنر', 'عمران', 'فنی'],
        'name': 'گروه معماری و نقشه کشی',
        'description': 'گروه معماری و نقشه‌کشی با ارائه آموزش‌های تخصصی در زمینه طراحی معماری، نقشه‌کشی ساختمان و مدیریت پروژه‌های عمرانی فعالیت می‌کند.',
        'goals': 'تربیت معماران و نقشه‌کشان ماهر با توانایی طراحی و اجرای پروژه‌های ساختمانی',
        'research_areas': 'معماری پایدار، طراحی داخلی، BIM، نقشه‌برداری',
        'order': 3,
    },
    {
        'dept_hints': ['مکانیک', 'فنی', 'مهندسی'],
        'name': 'گروه مکانیک',
        'description': 'گروه مکانیک با تدریس مبانی طراحی مکانیکی، دینامیک، ترمودینامیک و ساخت و تولید، دانشجویان را برای فعالیت در صنایع آماده می‌کند.',
        'goals': 'تربیت مهندسان مکانیک توانمند با دانش تئوری و مهارت‌های عملی کارگاهی',
        'research_areas': 'طراحی مکانیکی، ساخت و تولید، ترمودینامیک، مکاترونیک',
        'order': 4,
    },
    {
        'dept_hints': ['حسابداری', 'مدیریت', 'اقتصاد'],
        'name': 'گروه حسابداری',
        'description': 'گروه حسابداری با ارائه آموزش‌های تخصصی در حسابداری مالی، حسابرسی، مالیات و حسابداری مدیریت، دانش‌آموختگان متخصص تربیت می‌کند.',
        'goals': 'تربیت حسابداران ماهر آشنا به استانداردهای حسابداری ایران و بین‌الملل',
        'research_areas': 'حسابداری مالی، حسابرسی، مالیات، سیستم‌های اطلاعاتی حسابداری',
        'order': 5,
    },
    {
        'dept_hints': ['مدیریت', 'اقتصاد', 'علوم انسانی'],
        'name': 'گروه مدیریت صنعتی و مالی',
        'description': 'گروه مدیریت صنعتی و مالی با تمرکز بر مدیریت تولید، برنامه‌ریزی استراتژیک و مدیریت مالی، مدیران توانمند تربیت می‌کند.',
        'goals': 'تربیت مدیران صنعتی و مالی با رویکرد تحلیلی و توانایی تصمیم‌گیری در محیط‌های پیچیده',
        'research_areas': 'مدیریت تولید، مدیریت مالی، تحقیق در عملیات، کسب‌وکار',
        'order': 6,
    },
    {
        'dept_hints': ['مدیریت', 'بازرگانی', 'اقتصاد'],
        'name': 'گروه مدیریت بازرگانی',
        'description': 'گروه مدیریت بازرگانی با آموزش بازاریابی، مدیریت بازرگانی، تجارت بین‌الملل و کارآفرینی، دانشجویان را برای دنیای کسب‌وکار آماده می‌کند.',
        'goals': 'تربیت مدیران بازرگانی توانمند با درک عمیق از بازارها و رفتار مصرف‌کننده',
        'research_areas': 'بازاریابی دیجیتال، تجارت الکترونیک، مدیریت زنجیره تامین',
        'order': 7,
    },
    {
        'dept_hints': ['علوم اجتماعی', 'علوم انسانی', 'جامعه'],
        'name': 'گروه علوم اجتماعی',
        'description': 'گروه علوم اجتماعی با بررسی و تحلیل پدیده‌های اجتماعی، فرهنگی و سیاسی، دانشجویان را برای فعالیت در حوزه‌های مددکاری و برنامه‌ریزی اجتماعی آماده می‌کند.',
        'goals': 'تربیت متخصصان علوم اجتماعی آگاه به مسائل جامعه ایران',
        'research_areas': 'جامعه‌شناسی، آسیب‌های اجتماعی، توسعه اجتماعی، فرهنگ‌شناسی',
        'order': 8,
    },
    {
        'dept_hints': ['روانشناسی', 'علوم انسانی', 'علوم اجتماعی'],
        'name': 'گروه روانشناسی',
        'description': 'گروه روانشناسی با تدریس مبانی روانشناسی عمومی، بالینی، صنعتی-سازمانی و مشاوره، دانشجویان را برای فعالیت در حوزه بهداشت روان آماده می‌کند.',
        'goals': 'تربیت روانشناسان متخصص آشنا به روش‌های ارزیابی و مداخله روانشناختی',
        'research_areas': 'روانشناسی بالینی، مشاوره، روانشناسی کودک، روانشناسی صنعتی',
        'order': 9,
    },
    {
        'dept_hints': ['علوم پایه', 'علوم', 'پایه'],
        'name': 'گروه علوم پایه و معارف',
        'description': 'گروه علوم پایه و معارف با تدریس دروس عمومی از جمله ریاضیات، فیزیک، شیمی و معارف اسلامی، پایه آموزش را برای تمام رشته‌ها فراهم می‌کند.',
        'goals': 'ارتقاء سطح دانش پایه دانشجویان در تمام رشته‌ها',
        'research_areas': 'ریاضیات کاربردی، فیزیک، معارف اسلامی، ادبیات فارسی',
        'order': 10,
    },
    {
        'dept_hints': ['تربیت', 'آموزش', 'علوم انسانی'],
        'name': 'گروه علوم تربیتی - مدیریت آموزشی',
        'description': 'گروه علوم تربیتی با تمرکز بر مدیریت آموزشی، برنامه‌ریزی درسی و روان‌شناسی تربیتی، مدیران و مربیان آموزشی تربیت می‌کند.',
        'goals': 'تربیت مدیران آموزشی با توانایی برنامه‌ریزی و اجرای برنامه‌های آموزشی',
        'research_areas': 'مدیریت آموزشی، برنامه‌ریزی درسی، یاددهی-یادگیری، ارزشیابی آموزشی',
        'order': 11,
    },
]


class Command(BaseCommand):
    help = 'Seed default academic groups (groups listed in navbar image)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Overwrite existing groups',
        )

    def out(self, msg):
        """Write to stdout safely regardless of terminal encoding."""
        try:
            self.stdout.write(msg)
        except (UnicodeEncodeError, UnicodeDecodeError):
            self.stdout.write(msg.encode('ascii', errors='replace').decode('ascii'))

    def handle(self, *args, **options):
        force = options['force']
        departments = list(Department.objects.filter(is_active=True))

        if not departments:
            self.out(self.style.WARNING('No active departments found. Creating a default one...'))
            dept, _ = Department.objects.get_or_create(
                slug='general',
                defaults={
                    'name': 'دانشکده عمومی',
                    'short_description': 'دانشکده عمومی دانشگاه',
                    'is_active': True,
                }
            )
            departments = [dept]

        created = 0
        skipped = 0

        for item in DEFAULT_GROUPS:
            hints = item.pop('dept_hints')
            name  = item['name']

            # Find best matching department
            matched_dept = None
            for hint in hints:
                for dept in departments:
                    if hint in dept.name:
                        matched_dept = dept
                        break
                if matched_dept:
                    break
            if not matched_dept:
                matched_dept = departments[0]

            if AcademicGroup.objects.filter(name=name).exists():
                if force:
                    AcademicGroup.objects.filter(name=name).update(**item)
                    self.out(f'  [updated] {name}')
                else:
                    self.out(f'  [skipped] {name}')
                skipped += 1
                item['dept_hints'] = hints
                continue

            # Ensure unique slug
            base_slug = slugify(name, allow_unicode=True)
            slug = base_slug
            counter = 1
            while AcademicGroup.objects.filter(slug=slug).exists():
                slug = f'{base_slug}-{counter}'
                counter += 1

            AcademicGroup.objects.create(department=matched_dept, slug=slug, **item)
            created += 1
            self.out(self.style.SUCCESS(f'  [created] {name}'))
            item['dept_hints'] = hints

        self.out('')
        self.out(self.style.SUCCESS(f'Done. Created: {created}  Skipped: {skipped}'))
        self.out('Manage groups at: /admin/academics/academicgroup/')
