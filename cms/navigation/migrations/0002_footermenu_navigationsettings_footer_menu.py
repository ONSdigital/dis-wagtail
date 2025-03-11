# Generated by Django 5.1.5 on 2025-02-10 11:30

import django.db.models.deletion
import wagtail.models
from django.db import migrations, models

import cms.core.fields


class Migration(migrations.Migration):
    dependencies = [
        ("navigation", "0001_initial"),
        ("wagtailcore", "0094_alter_page_locale"),
    ]

    operations = [
        migrations.CreateModel(
            name="FooterMenu",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("live", models.BooleanField(default=True, editable=False)),
                ("has_unpublished_changes", models.BooleanField(default=False, editable=False)),
                ("first_published_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("last_published_at", models.DateTimeField(editable=False, null=True)),
                ("go_live_at", models.DateTimeField(blank=True, null=True)),
                ("expire_at", models.DateTimeField(blank=True, null=True)),
                ("expired", models.BooleanField(default=False, editable=False)),
                ("columns", cms.core.fields.StreamField(blank=True, block_lookup={})),
                (
                    "latest_revision",
                    models.ForeignKey(
                        blank=True,
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="wagtailcore.revision",
                    ),
                ),
                (
                    "live_revision",
                    models.ForeignKey(
                        blank=True,
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="wagtailcore.revision",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
            bases=(wagtail.models.PreviewableMixin, models.Model),
        ),
        migrations.AddField(
            model_name="navigationsettings",
            name="footer_menu",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="navigation.footermenu",
            ),
        ),
    ]
