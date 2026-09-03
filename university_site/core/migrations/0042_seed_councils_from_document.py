"""شوراهای سند رسمی را همان موقع دیپلوی می‌ریزد.

سرور ترمینال ندارد، پس دستور seed_councils دستی اجرا نمی‌شود؛
migrate در دیپلوی خودکار اجرا می‌شود و این مهاجرت همان کار را
می‌کند. تکرارش هم بی‌خطر است: شورایی که هست دست نمی‌خورد، پس متنی
که مدیر از پنل ویرایش کرده بازنویسی نمی‌شود.
"""
from django.db import migrations

from core.management.commands.seed_councils import COUNCILS

# شوراهای حدسیِ قدیم که در سند نیستند؛ حذف نمی‌شوند، فقط از سایت
# برداشته می‌شوند تا اگر متنی رویشان بوده از دست نرود.
RETIRED = ['shoraye-moassese', 'shoraye-farhangi', 'komite-enzebati']


def forwards(apps, schema_editor):
    Council = apps.get_model('core', 'Council')
    for row in COUNCILS:
        Council.objects.get_or_create(
            slug=row['slug'], defaults={**row, 'is_active': True})
    Council.objects.filter(slug__in=RETIRED).update(is_active=False)


def backwards(apps, schema_editor):
    """شوراهای سند را برمی‌دارد و حدس قدیمی را برمی‌گرداند."""
    Council = apps.get_model('core', 'Council')
    Council.objects.filter(
        slug__in=[row['slug'] for row in COUNCILS]).delete()
    Council.objects.filter(slug__in=RETIRED).update(is_active=True)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0041_sitesettings_council_card_min_height_and_more'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
