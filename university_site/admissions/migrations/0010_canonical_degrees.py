from django.db import migrations, models


def forwards(apps, schema_editor):
    Application = apps.get_model('admissions', 'Application')
    AdmissionInfo = apps.get_model('admissions', 'AdmissionInfo')
    mapping = {
        'associate': 'associate_cont',
        'bachelor': 'bachelor_cont',
        'phd': 'master',
    }
    for old, new in mapping.items():
        Application.objects.filter(degree=old).update(degree=new)
        for info in list(AdmissionInfo.objects.filter(degree=old)):
            if AdmissionInfo.objects.filter(degree=new).exists():
                info.is_active = False
                info.save(update_fields=['is_active'])
            else:
                info.degree = new
                info.save(update_fields=['degree'])


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('admissions', '0009_alter_application_prev_degree'),
    ]

    operations = [
        migrations.AlterField(
            model_name='admissioninfo',
            name='degree',
            field=models.CharField(
                choices=[
                    ('associate_cont', 'کاردانی پیوسته'),
                    ('bachelor_disc', 'کارشناسی ناپیوسته'),
                    ('bachelor_cont', 'کارشناسی پیوسته'),
                    ('associate_tech', 'کاردانی فنی'),
                    ('master', 'کارشناسی ارشد'),
                    ('associate', 'کاردانی'),
                    ('bachelor', 'کارشناسی'),
                    ('phd', 'دکتری'),
                ],
                max_length=20,
                unique=True,
                verbose_name='مقطع',
            ),
        ),
        migrations.AlterField(
            model_name='application',
            name='degree',
            field=models.CharField(
                choices=[
                    ('associate_cont', 'کاردانی پیوسته'),
                    ('bachelor_disc', 'کارشناسی ناپیوسته'),
                    ('bachelor_cont', 'کارشناسی پیوسته'),
                    ('associate_tech', 'کاردانی فنی'),
                    ('master', 'کارشناسی ارشد'),
                    ('associate', 'کاردانی'),
                    ('bachelor', 'کارشناسی'),
                    ('phd', 'دکتری'),
                ],
                max_length=20,
                verbose_name='مقطع',
            ),
        ),
        migrations.RunPython(forwards, backwards),
    ]
