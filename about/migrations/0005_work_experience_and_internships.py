# Generated by Django 5.1 on 2024-12-11 10:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("about", "0004_certification_link_title_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Work_Experience_and_Internships",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100)),
                ("title", models.CharField(max_length=200)),
                ("content", models.CharField()),
            ],
        ),
    ]
