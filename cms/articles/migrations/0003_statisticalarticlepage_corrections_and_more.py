# Generated by Django 5.1.7 on 2025-03-20 12:22

import cms.core.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('articles', '0002_articleseriespage_listing_image_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='statisticalarticlepage',
            name='corrections',
            field=cms.core.fields.StreamField(blank=True, block_lookup={}),
        ),
        migrations.AddField(
            model_name='statisticalarticlepage',
            name='notices',
            field=cms.core.fields.StreamField(blank=True, block_lookup={}),
        ),
    ]
