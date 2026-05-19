# Generated migration to remove APIConfig model

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('configuration', '0002_remove_crmconfig'),
    ]

    operations = [
        migrations.DeleteModel(
            name='APIConfig',
        ),
    ]
