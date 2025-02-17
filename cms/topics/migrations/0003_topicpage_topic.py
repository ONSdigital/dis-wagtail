# Generated by Django 5.1.6 on 2025-02-17 14:10

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("taxonomy", "0001_initial"),
        ("topics", "0002_featured_series_explore_more_related"),
    ]

    operations = [
        migrations.AddField(
            model_name="topicpage",
            name="topic",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="related_%(class)s",
                to="taxonomy.topic",
            ),
        ),
    ]
