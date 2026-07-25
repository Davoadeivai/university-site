from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admissions', '0007_prev_degree_discontinuous'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='photo_hijab_confirmed',
            field=models.BooleanField(
                default=False,
                help_text='برای متقاضیان خانم الزامی است.',
                verbose_name='تأیید حجاب کامل در عکس پرسنلی',
            ),
        ),
    ]
