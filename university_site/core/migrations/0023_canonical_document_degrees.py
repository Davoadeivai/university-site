from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0022_sitesettings_org_chart_file'),
    ]

    operations = [
        migrations.AlterField(
            model_name='downloadabledocument',
            name='degree_level',
            field=models.CharField(
                choices=[
                    ('general', 'عمومی (بدون پوشه مقطع)'),
                    ('associate_cont', 'کاردانی پیوسته'),
                    ('bachelor_discontinuous', 'کارشناسی ناپیوسته'),
                    ('bachelor_continuous', 'کارشناسی پیوسته'),
                    ('associate_tech', 'کاردانی فنی'),
                    ('master', 'کارشناسی ارشد'),
                    ('associate', 'کاردانی ناپیوسته'),
                ],
                db_index=True,
                default='general',
                help_text='سند در کدام پوشه مقطع نمایش داده شود — حتماً یکی را انتخاب کنید',
                max_length=40,
                verbose_name='مقطع / پوشه',
            ),
        ),
    ]
