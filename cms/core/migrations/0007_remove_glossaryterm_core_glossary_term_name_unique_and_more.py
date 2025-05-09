# Generated by Django 5.1.7 on 2025-04-10 09:33

import uuid

import django.db.models.deletion
import django.db.models.functions.text
from django.db import migrations, models
from wagtail.models import BootstrapTranslatableModel


def add_new_locale(apps, schema_editor):
    Locale = apps.get_model("wagtailcore", "Locale")
    Locale.objects.update_or_create(language_code="cy")


def remove_new_locale(apps, schema_editor):
    Locale = apps.get_model("wagtailcore", "Locale")
    Locale.objects.filter(language_code="cy").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0006_update_user_groups"),
        ("wagtailcore", "0094_alter_page_locale"),
    ]

    operations = [
        migrations.RunPython(
            code=add_new_locale,
            reverse_code=remove_new_locale,
        ),
        migrations.RemoveConstraint(
            model_name="glossaryterm",
            name="core_glossary_term_name_unique",
        ),
        migrations.RemoveConstraint(
            model_name="glossaryterm",
            name="unique_translation_key_locale_core_glossaryterm",
        ),
        migrations.AddField(
            model_name="contactdetails",
            name="locale",
            field=models.ForeignKey(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="wagtailcore.locale",
            ),
        ),
        migrations.AddField(
            model_name="contactdetails",
            name="translation_key",
            field=models.UUIDField(editable=False, null=True),
        ),
        migrations.AlterUniqueTogether(
            name="glossaryterm",
            unique_together={("name", "locale"), ("translation_key", "locale")},
        ),
        BootstrapTranslatableModel("core.ContactDetails"),
        migrations.RemoveConstraint(
            model_name="contactdetails",
            name="core_contactdetails_name_unique",
        ),
        migrations.AlterField(
            model_name="contactdetails",
            name="locale",
            field=models.ForeignKey(
                editable=False, on_delete=django.db.models.deletion.PROTECT, related_name="+", to="wagtailcore.locale"
            ),
        ),
        migrations.AlterField(
            model_name="contactdetails",
            name="translation_key",
            field=models.UUIDField(default=uuid.uuid4, editable=False),
        ),
        migrations.AlterUniqueTogether(
            name="contactdetails",
            unique_together={("translation_key", "locale")},
        ),
        migrations.AddConstraint(
            model_name="contactdetails",
            constraint=models.UniqueConstraint(
                django.db.models.functions.text.Lower("name"),
                django.db.models.functions.text.Lower("email"),
                models.F("locale"),
                name="core_contactdetails_name_unique",
                violation_error_message="Contact details with this name and email combination already exists.",
            ),
        ),
    ]
