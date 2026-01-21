import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def _update_permissions(permission_model, renames: list[tuple[str, str, str]]) -> None:
    """Update permission codenames and names.

    Args:
        permission_model: The Permission model from apps.get_model().
        renames: List of (old_codename, new_codename, new_name) tuples.
    """
    for old_codename, new_codename, new_name in renames:
        try:
            permission = permission_model.objects.get(codename=old_codename, content_type__app_label="core")
            permission.codename = new_codename
            permission.name = new_name
            permission.save()
        except permission_model.DoesNotExist:
            pass


def rename_permissions(apps, schema_editor):
    """Rename permission codenames from glossaryterm to definition."""
    _update_permissions(
        apps.get_model("auth", "Permission"),
        [
            ("add_glossaryterm", "add_definition", "Can add definition"),
            ("change_glossaryterm", "change_definition", "Can change definition"),
            ("delete_glossaryterm", "delete_definition", "Can delete definition"),
            ("view_glossaryterm", "view_definition", "Can view definition"),
        ],
    )


def reverse_rename_permissions(apps, schema_editor):
    """Reverse the permission rename from definition back to glossaryterm."""
    _update_permissions(
        apps.get_model("auth", "Permission"),
        [
            ("add_definition", "add_glossaryterm", "Can add glossary term"),
            ("change_definition", "change_glossaryterm", "Can change glossary term"),
            ("delete_definition", "delete_glossaryterm", "Can delete glossary term"),
            ("view_definition", "view_glossaryterm", "Can view glossary term"),
        ],
    )


class Migration(migrations.Migration):
    """Rename GlossaryTerm model to Definition.

    This migration renames the model, updates related names on foreign keys,
    and updates permission codenames to use the new 'definition' terminology.
    """

    dependencies = [
        ("core", "0010_migrate_imageblock_caption"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameModel(
            old_name="GlossaryTerm",
            new_name="Definition",
        ),
        migrations.AlterModelOptions(
            name="definition",
            options={"verbose_name": "definition", "verbose_name_plural": "definitions"},
        ),
        migrations.AlterField(
            model_name="definition",
            name="owner",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="owned_definitions",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(rename_permissions, reverse_rename_permissions),
    ]
