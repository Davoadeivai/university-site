# Generated manually for removing food/dorm automation URL fields

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_eservices_quick_access_official'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='sitesettings',
            name='external_dorm_url',
        ),
        migrations.RemoveField(
            model_name='sitesettings',
            name='external_food_url',
        ),
    ]
