# Generated by Django 5.1.4 on 2025-01-17 13:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('datavis', '0002_datasource_column_count'),
    ]

    operations = [
        migrations.AddField(
            model_name='chart',
            name='marker_style',
            field=models.CharField(blank=True, default='', max_length=15),
        ),
    ]
