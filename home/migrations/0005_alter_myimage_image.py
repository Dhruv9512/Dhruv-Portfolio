# Generated by Django 5.1.4 on 2024-12-21 08:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0004_alter_myimage_image'),
    ]

    operations = [
        migrations.AlterField(
            model_name='myimage',
            name='image',
            field=models.CharField(),
        ),
    ]
