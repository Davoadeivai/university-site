"""ابعاد اسلایدهایی که پیش از این آپلود شده‌اند.

`width_field` فقط هنگام ذخیرهٔ تازه پر می‌شود، پس اسلایدهای موجود
بدون ابعاد می‌مانند و تصمیم «کامل نشان بده یا قاب را پر کن» برایشان
به پیش‌فرض می‌افتد. اینجا یک بار فایل‌ها خوانده می‌شوند.

فایلی که خوانده نشود — پاک‌شده، خراب، یا Pillow نصب‌نبوده — از قلم
می‌افتد و مهاجرت ادامه پیدا می‌کند: هیچ ابعادی نباید جلوی به‌روزرسانی
سایت را بگیرد.
"""
from django.db import migrations


def fill(apps, schema_editor):
    Slider = apps.get_model('core', 'Slider')
    for row in Slider.objects.all():
        if row.image_width and row.image_height:
            continue
        try:
            width, height = row.image.width, row.image.height
        except Exception:
            continue
        Slider.objects.filter(pk=row.pk).update(
            image_width=width, image_height=height)


def unfill(apps, schema_editor):
    """برگشت‌پذیر: ابعاد داده نیستند، فقط یادداشت."""
    apps.get_model('core', 'Slider').objects.update(
        image_width=None, image_height=None)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0049_slider_fit_slider_focus_slider_image_height_and_more'),
    ]

    operations = [migrations.RunPython(fill, unfill)]
