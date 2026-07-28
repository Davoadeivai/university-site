from django.db import migrations, models


def forwards(apps, schema_editor):
    Major = apps.get_model('academics', 'Major')
    mapping = {
        'associate': 'associate_cont',
        'associate_disc': 'associate_cont',
        'bachelor': 'bachelor_cont',
        'phd': 'master',
    }
    for old, new in mapping.items():
        Major.objects.filter(degree=old).update(degree=new)


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0004_major_curriculum_files'),
    ]

    operations = [
        migrations.AlterField(
            model_name='major',
            name='degree',
            field=models.CharField(
                choices=[
                    ('associate_cont', 'کاردانی پیوسته'),
                    ('bachelor_disc', 'کارشناسی ناپیوسته'),
                    ('bachelor_cont', 'کارشناسی پیوسته'),
                    ('associate_tech', 'کاردانی فنی'),
                    ('master', 'کارشناسی ارشد'),
                    ('associate_disc', 'کاردانی ناپیوسته'),
                    ('associate', 'کاردانی'),
                    ('bachelor', 'کارشناسی'),
                    ('phd', 'دکتری'),
                ],
                max_length=20,
                verbose_name='مقطع تحصیلی',
            ),
        ),
        migrations.RunPython(forwards, backwards),
    ]
