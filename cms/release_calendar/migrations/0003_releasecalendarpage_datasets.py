# Generated by Django 5.1.7 on 2025-04-02 11:25

from django.db import migrations

import cms.core.fields


class Migration(migrations.Migration):
    dependencies = [
        ("release_calendar", "0002_create_releasecalendarindex"),
    ]

    operations = [
        migrations.AddField(
            model_name="releasecalendarpage",
            name="datasets",
            field=cms.core.fields.StreamField(blank=True, block_lookup={}, default=list),
        ),
    ]
