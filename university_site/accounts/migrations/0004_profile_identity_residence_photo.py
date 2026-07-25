from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_userprofile_major'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='address',
            field=models.TextField(blank=True, verbose_name='آدرس'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='city',
            field=models.CharField(blank=True, max_length=100, verbose_name='شهر'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='father_name',
            field=models.CharField(blank=True, max_length=100, verbose_name='نام پدر'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='gender',
            field=models.CharField(blank=True, choices=[('male', 'مرد'), ('female', 'زن')], max_length=10, verbose_name='جنسیت'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='gpa',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=4, null=True, verbose_name='معدل'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='military',
            field=models.CharField(blank=True, choices=[('done', 'پایان خدمت'), ('exempt', 'معاف'), ('studying', 'در حال تحصیل / معافیت تحصیلی'), ('na', 'مشمول نیست')], default='na', max_length=20, verbose_name='وضعیت نظام وظیفه'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='phone_emergency',
            field=models.CharField(blank=True, max_length=15, verbose_name='تلفن اضطراری'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='photo_hijab_confirmed',
            field=models.BooleanField(default=False, help_text='برای بانوان: تأیید می‌کنم عکس با حجاب کامل اسلامی است.', verbose_name='تأیید حجاب کامل در عکس'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='postal_code',
            field=models.CharField(blank=True, max_length=10, verbose_name='کد پستی'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='prev_degree',
            field=models.CharField(blank=True, choices=[('diploma', 'دیپلم'), ('associate', 'کاردانی'), ('bachelor', 'کارشناسی'), ('discontinuous_bachelor', 'کارشناسی ناپیوسته'), ('master', 'کارشناسی ارشد')], max_length=30, verbose_name='آخرین مدرک'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='prev_grad_year',
            field=models.CharField(blank=True, max_length=10, verbose_name='سال فارغ‌التحصیلی'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='prev_major',
            field=models.CharField(blank=True, max_length=200, verbose_name='رشته مدرک قبلی'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='prev_school',
            field=models.CharField(blank=True, max_length=200, verbose_name='مدرسه / دانشگاه قبلی'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='province',
            field=models.CharField(blank=True, max_length=100, verbose_name='استان'),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='avatar',
            field=models.ImageField(blank=True, help_text='عکس رسمی ۳×۴؛ برای بانوان با حجاب کامل الزامی است.', null=True, upload_to='avatars/', verbose_name='عکس پرسنلی'),
        ),
    ]
