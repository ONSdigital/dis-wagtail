# Generated by Django 5.1.8 on 2025-04-16 11:46

from django.db import migrations, models

import cms.core.fields


class Migration(migrations.Migration):
    dependencies = [
        ("articles", "0003_statisticalarticlepage_corrections_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="statisticalarticlepage",
            name="dataset_sorting",
            field=models.CharField(default="AS_SHOWN", max_length=32),
        ),
        migrations.AddField(
            model_name="statisticalarticlepage",
            name="datasets",
            field=cms.core.fields.StreamField(blank=True, block_lookup={}, default=list),
        ),
    ]
