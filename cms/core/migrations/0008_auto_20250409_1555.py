# Generated by Django 5.1.7 on 2025-04-09 14:55

from django.db import migrations
from wagtail.models import BootstrapTranslatableModel


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0007_remove_glossaryterm_core_glossary_term_name_unique_and_more"),
    ]

    operations = [
        BootstrapTranslatableModel("core.ContactDetails"),
    ]
