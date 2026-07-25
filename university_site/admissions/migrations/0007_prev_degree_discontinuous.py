from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admissions', '0006_application_phone_optional'),
    ]

    operations = [
        migrations.AlterField(
            model_name='application',
            name='prev_degree',
            field=models.CharField(
                choices=[
                    ('diploma', 'دیپلم'),
                    ('associate', 'کاردانی'),
                    ('bachelor', 'کارشناسی'),
                    ('discontinuous_bachelor', 'کارشناسی ناپیوسته'),
                    ('master', 'کارشناسی ارشد'),
                ],
                default='diploma',
                max_length=20,
                verbose_name='آخرین مدرک',
            ),
        ),
        migrations.AlterField(
            model_name='application',
            name='know_from',
            field=models.CharField(
                choices=[
                    ('social', 'شبکه‌های اجتماعی'),
                    ('friend', 'معرفی دوست/آشنا'),
                    ('site', 'وب‌سایت دانشگاه'),
                    ('exhibition', 'نمایشگاه'),
                    ('search', 'موتورهای جستجو'),
                    ('other', 'سایر'),
                ],
                default='site',
                max_length=20,
                verbose_name='نحوه آشنایی',
            ),
        ),
    ]
