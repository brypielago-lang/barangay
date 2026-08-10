from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='barangayprofile',
            name='municipality_logo',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to='branding/municipality/',
            ),
        ),
    ]
