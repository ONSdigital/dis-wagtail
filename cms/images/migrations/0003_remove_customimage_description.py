# Generated by Django 5.1.2 on 2024-11-06 11:47

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("images", "0002_customimage_description"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="customimage",
            name="description",
        ),
    ]
