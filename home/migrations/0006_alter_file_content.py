# Generated by Django 5.1.4 on 2024-12-21 09:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0005_alter_myimage_image'),
    ]

    operations = [
        migrations.AlterField(
            model_name='file',
            name='content',
            field=models.CharField(),
        ),
    ]