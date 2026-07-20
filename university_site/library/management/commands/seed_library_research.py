from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from library.models import Article, Book
from research.models import (
    Conference,
    IndustryPartnership,
    Journal,
    ResearchProject,
    Thesis,
)


class Command(BaseCommand):
    help = 'Seed demo data for library catalog and research hub'

    def handle(self, *args, **options):
        books = [
            ('ساختار داده و الگوریتم', 'دکتر رضایی', 'نشر دانشگاهی', 1401, 'علوم کامپیوتر', 'فارسی', 'A-12'),
            ('مدارهای الکتریکی', 'مهندس کریمی', 'آوای دانش', 1399, 'مهندسی برق', 'فارسی', 'B-03'),
            ('مدیریت استراتژیک', 'عباس نوری', 'سازمان مدیریت', 1400, 'مدیریت', 'فارسی', 'C-08'),
            ('Introduction to AI', 'Russell & Norvig', 'Pearson', 2021, 'علوم کامپیوتر', 'انگلیسی', 'A-20'),
            ('مکانیک سیالات', 'وایت', 'نشر صنعتی', 1398, 'مهندسی مکانیک', 'فارسی', 'D-01'),
            ('حقوق مدنی', 'دکتر کاتوزیان', 'شرکت سهامی انتشار', 1397, 'حقوق', 'فارسی', 'E-05'),
        ]
        for title, author, publisher, year, subject, language, location in books:
            Book.objects.get_or_create(
                title=title,
                author=author,
                defaults={
                    'publisher': publisher,
                    'year': year,
                    'subject': subject,
                    'language': language,
                    'location': location,
                    'description': f'کتاب {title} در موضوع {subject}.',
                    'copies_available': 3,
                    'is_available': True,
                    'isbn': f'978-{year}-00{year % 100}',
                },
            )

        articles = [
            ('یادگیری عمیق در پردازش تصویر', 'احمدی، موسوی', 'مجله هوش مصنوعی', 1402, 'یادگیری ماشین, تصویر'),
            ('شبکه‌های حسگر بی‌سیم', 'حسینی', 'نشریه مهندسی برق', 1401, 'مخابرات, IoT'),
            ('رفتار مصرف‌کننده آنلاین', 'نوری، اکبری', 'پژوهش‌های مدیریت', 1400, 'بازاریابی'),
        ]
        for title, authors, journal, year, keywords in articles:
            Article.objects.get_or_create(
                title=title,
                authors=authors,
                defaults={
                    'journal': journal,
                    'year': year,
                    'keywords': keywords,
                    'abstract': f'چکیده نمونه برای مقاله «{title}».',
                    'doi': f'10.1000/demo.{year}',
                },
            )

        for title, researcher, status, featured in [
            ('بهینه‌سازی مصرف انرژی در ساختمان‌های هوشمند', 'دکتر احمدی', 'ongoing', True),
            ('تحلیل داده‌های سلامت با یادگیری ماشین', 'دکتر موسوی', 'ongoing', True),
            ('توسعه حسگرهای نوری ارزان‌قیمت', 'مهندس رضایی', 'completed', False),
        ]:
            ResearchProject.objects.get_or_create(
                title=title,
                defaults={
                    'researcher': researcher,
                    'description': f'توضیحات پروژه پژوهشی: {title}',
                    'start_date': date.today() - timedelta(days=200),
                    'end_date': date.today() + timedelta(days=180) if status == 'ongoing' else date.today() - timedelta(days=30),
                    'budget': 250000000,
                    'status': status,
                    'is_featured': featured,
                },
            )

        for title, issn in [
            ('مجله مهندسی برق و کامپیوتر', '1234-5678'),
            ('فصلنامه مدیریت و اقتصاد', '2345-6789'),
        ]:
            slug = slugify(title, allow_unicode=True) or f'journal-{issn}'
            Journal.objects.get_or_create(
                slug=slug,
                defaults={
                    'title': title,
                    'issn': issn,
                    'description': f'مجله علمی {title}',
                    'is_active': True,
                },
            )

        for title, author, supervisor, degree, year, dept in [
            ('طراحی سامانه توصیه‌گر آموزشی', 'علی محمدی', 'دکتر رضایی', 'master', 1402, 'فنی مهندسی'),
            ('مدل‌سازی ریسک اعتباری', 'سارا احمدی', 'دکتر نوری', 'phd', 1401, 'مدیریت'),
            ('تحلیل شبکه‌های اجتماعی فارسی', 'رضا کریمی', 'دکتر موسوی', 'master', 1400, 'فنی مهندسی'),
        ]:
            Thesis.objects.get_or_create(
                title=title,
                author=author,
                defaults={
                    'supervisor': supervisor,
                    'degree': degree,
                    'year': year,
                    'department': dept,
                    'abstract': f'چکیده پایان‌نامه «{title}» نوشته {author}.',
                    'keywords': 'پژوهش, داده, دانشگاه',
                },
            )

        Conference.objects.get_or_create(
            title='همایش ملی هوش مصنوعی و کاربردها',
            date=date.today() + timedelta(days=45),
            defaults={
                'description': 'همایش سالانه با محوریت هوش مصنوعی کاربردی.',
                'location': 'سالن همایش‌های دانشگاه',
                'organizer': 'معاونت پژوهشی',
                'is_upcoming': True,
            },
        )
        Conference.objects.get_or_create(
            title='کنفرانس مهندسی برق ۱۴۰۱',
            date=date.today() - timedelta(days=400),
            defaults={
                'description': 'دوره قبلی کنفرانس مهندسی برق.',
                'location': 'تهران',
                'organizer': 'انجمن مهندسی برق',
                'is_upcoming': False,
            },
        )

        IndustryPartnership.objects.get_or_create(
            company_name='شرکت فناوری نمونه',
            defaults={
                'description': 'همکاری در پروژه‌های کاربردی',
                'partnership_type': 'تحقیق و توسعه',
                'is_active': True,
            },
        )

        self.stdout.write(self.style.SUCCESS('Library and research demo data ready.'))
