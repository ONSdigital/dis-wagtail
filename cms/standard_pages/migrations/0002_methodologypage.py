# Generated by Django 5.1.3 on 2024-12-11 13:45

import django.db.models.deletion
import wagtail.fields
from django.db import migrations, models

import cms.core.fields


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0004_contactdetails_core_contactdetails_name_unique"),
        ("images", "0002_customimage_description"),
        ("standard_pages", "0001_initial"),
        ("wagtailcore", "0094_alter_page_locale"),
    ]

    operations = [
        migrations.CreateModel(
            name="MethodologyPage",
            fields=[
                (
                    "page_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="wagtailcore.page",
                    ),
                ),
                ("listing_title", models.CharField(blank=True, max_length=255)),
                ("listing_summary", models.CharField(blank=True, max_length=255)),
                ("social_text", models.CharField(blank=True, max_length=255)),
                ("summary", wagtail.fields.RichTextField()),
                ("published_date", models.DateField()),
                ("last_revised_date", models.DateField(blank=True, null=True)),
                ("content", cms.core.fields.StreamField(block_lookup={})),
                ("show_cite_this_page", models.BooleanField(default=True)),
                (
                    "contact_details",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="core.contactdetails",
                    ),
                ),
                (
                    "listing_image",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="images.customimage",
                    ),
                ),
                (
                    "social_image",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="images.customimage",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
            bases=("wagtailcore.page", models.Model),
        ),
    ]
