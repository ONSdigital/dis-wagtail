from django.db import migrations


def backfill_alias_last_published_at(apps, schema_editor):
    Page = apps.get_model("wagtailcore.Page")
    aliases = Page.objects.filter(alias_of__isnull=False, last_published_at__isnull=True).select_related("alias_of")
    to_update = []
    for alias in aliases:
        if alias.alias_of.last_published_at:
            alias.last_published_at = alias.alias_of.last_published_at
            to_update.append(alias)
    Page.objects.bulk_update(to_update, ["last_published_at"])


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0015_delete_existing_page_view_restrictions"),
    ]

    operations = [
        migrations.RunPython(backfill_alias_last_published_at, reverse_code=migrations.RunPython.noop),
    ]
