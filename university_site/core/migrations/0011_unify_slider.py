# Generated manually — unify Slider, remove LandingSlider

from django.db import migrations, models


def copy_landing_to_slider(apps, schema_editor):
    Slider = apps.get_model('core', 'Slider')
    LandingSlider = apps.get_model('core', 'LandingSlider')
    if Slider.objects.exists():
        # فقط اسلایدرهای کمکی که هنوز منتقل نشده‌اند
        pass
    offset = Slider.objects.count()
    for i, ls in enumerate(LandingSlider.objects.all().order_by('order')):
        Slider.objects.create(
            title=ls.title,
            subtitle=ls.subtitle or '',
            image=ls.image,
            link=ls.btn1_url or '',
            link_text=ls.btn1_text or '',
            btn2_text=ls.btn2_text or '',
            btn2_url=ls.btn2_url or '',
            badge_text=ls.badge_text or '',
            badge_color=ls.badge_color or 'danger',
            badge_icon=ls.badge_icon or 'fas fa-bell',
            order=offset + i,
            is_active=ls.is_active,
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_landing_slider'),
    ]

    operations = [
        migrations.AddField(
            model_name='slider',
            name='btn2_text',
            field=models.CharField(blank=True, max_length=80, verbose_name='متن دکمه دوم'),
        ),
        migrations.AddField(
            model_name='slider',
            name='btn2_url',
            field=models.CharField(blank=True, max_length=300, verbose_name='لینک دکمه دوم'),
        ),
        migrations.AlterField(
            model_name='slider',
            name='link',
            field=models.CharField(blank=True, max_length=300, verbose_name='لینک دکمه اول'),
        ),
        migrations.AlterField(
            model_name='slider',
            name='link_text',
            field=models.CharField(blank=True, max_length=100, verbose_name='متن دکمه اول'),
        ),
        migrations.AlterField(
            model_name='slider',
            name='subtitle',
            field=models.CharField(blank=True, max_length=400, verbose_name='زیرعنوان'),
        ),
        migrations.AlterField(
            model_name='slider',
            name='badge_color',
            field=models.CharField(
                blank=True,
                choices=[
                    ('danger', 'قرمز (فوری)'),
                    ('warning', 'زرد (هشدار)'),
                    ('success', 'سبز (اطلاع)'),
                    ('info', 'آبی روشن'),
                    ('primary', 'آبی'),
                    ('gold', 'طلایی'),
                    ('dark', 'تیره'),
                ],
                default='danger',
                help_text='رنگ پس‌زمینه برچسب اعلان',
                max_length=20,
                verbose_name='رنگ اعلان',
            ),
        ),
        migrations.RunPython(copy_landing_to_slider, noop_reverse),
        migrations.DeleteModel(name='LandingSlider'),
    ]
