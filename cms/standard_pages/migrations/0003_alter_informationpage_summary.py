# Generated by Django 5.1.5 on 2025-01-29 13:09

import wagtail.fields
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("standard_pages", "0002_indexpage"),
    ]

    operations = [
        migrations.AlterField(
            model_name="informationpage",
            name="summary",
            field=wagtail.fields.RichTextField(),
        ),
    ]
