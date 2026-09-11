"""کاشی «ارسال فیش واریزی» را در دسترسی سریع صفحهٔ اصلی می‌گذارد.

    python manage.py seed_receipt_link

چرا دستور جدا و نه اضافه‌کردن به \u200Esync_official_eservices\u200E: آن دستور
پیش از کاشتن، همهٔ \u200EQuickLink\u200Eهای سه دستهٔ خود را پاک می‌کند. برای
همین هم در فهرست دیپلوی نیست — اگر هر بار اجرا می‌شد، لینکی که
موسسه در پنل اضافه کرده بود با دیپلوی بعدی از بین می‌رفت.

این یکی برعکس است: فقط اگر نبود می‌سازد، و اگر موسسه عنوان یا ترتیبش
را در پنل عوض کرده باشد دست نمی‌زند. تنها چیزی که هر بار تضمین
می‌کند، درستیِ خودِ نشانی است — چون آن نشانی را کد تعیین می‌کند نه
موسسه، و اگر روزی مسیر فرم عوض شود این کاشی نباید به ۴۰۴ برود.
"""
from django.core.management.base import BaseCommand
from django.urls import reverse

TITLE = 'ارسال فیش واریزی'
ICON = 'fas fa-receipt'

# کنارِ «شناسه واریز شهریه» می‌نشیند: دانشجویی که یکی را می‌خواهد،
# معمولاً دنبال آن یکی هم هست.
ORDER = 6


class Command(BaseCommand):
    help = 'کاشی ارسال فیش واریزی را در دسترسی سریع می‌گذارد'

    def handle(self, *args, **options):
        from core.models import QuickLink

        url = '%s?to=tuition_receipt' % reverse('contact:contact')

        # شناسهٔ کاشی، همان \u200Etuition_receipt\u200E داخل نشانی است و بس.
        #
        # اول با مسیرِ کاملِ فرم هم تطبیق داده می‌شد، ولی آن دقیقاً
        # حالتی را از دست می‌داد که این دستور برایش هست: نشانیِ
        # از-جا-دررفته. کاشیِ خراب پیدا نمی‌شد و به‌جای اصلاحش، یک
        # کاشی دوم ساخته می‌شد.
        row = QuickLink.objects.filter(
            category='home', url__contains='tuition_receipt').first()

        if row is None:
            QuickLink.objects.create(
                title=TITLE, icon=ICON, url=url, category='home',
                order=ORDER, open_in_new_tab=False, is_active=True)
            self.stdout.write(self.style.SUCCESS('+ %s' % TITLE))
            return

        # عنوان و ترتیب مالِ موسسه است؛ نشانی مالِ کد.
        if row.url != url:
            row.url = url
            row.save(update_fields=['url'])
            self.stdout.write('~ نشانی %s اصلاح شد' % row.title)
        else:
            self.stdout.write('= %s از قبل بود' % row.title)
