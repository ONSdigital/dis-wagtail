# Generated by Django 5.1.6 on 2025-03-06 13:56

import uuid

import django.db.models.deletion
import django.db.models.functions.text
import wagtail.fields
import wagtail.models
import wagtail.search.index
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0004_contactdetails_core_contactdetails_name_unique"),
        ("wagtailcore", "0094_alter_page_locale"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="GlossaryTerm",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ("translation_key", models.UUIDField(default=uuid.uuid4, editable=False)),
                ("name", models.CharField(max_length=255)),
                ("definition", wagtail.fields.RichTextField()),
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
                    "locale",
                    models.ForeignKey(
                        editable=False,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="wagtailcore.locale",
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="owned_glossary_terms",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="glossary_terms",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        django.db.models.functions.text.Lower("name"),
                        name="core_glossary_term_name_unique",
                        violation_error_message="A glossary term with this name already exists.",
                    ),
                    models.UniqueConstraint(
                        fields=("translation_key", "locale"), name="unique_translation_key_locale_core_glossaryterm"
                    ),
                ],
            },
            bases=(wagtail.models.PreviewableMixin, wagtail.search.index.Indexed, models.Model),
        ),
    ]
