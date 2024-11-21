from django.conf import settings
from django.db import migrations


def update_user_groups(apps, schema_editor):
    """Update the core user groups for the CMS."""
    ContentType = apps.get_model("contenttypes.ContentType")
    Permission = apps.get_model("auth.Permission")
    Group = apps.get_model("auth.Group")

    # Get content types
    wagtailadmin_content_type = ContentType.objects.get(
        app_label="wagtailadmin",
        model="admin",
    )

    # Get permissions
    admin_permission = Permission.objects.get(content_type=wagtailadmin_content_type, codename="access_admin")

    # Create 'Viewers' group
    viewer_group, _ = Group.objects.get_or_create(name=settings.VIEWERS_GROUP_NAME)
    viewer_group.permissions.add(admin_permission)
    viewer_group.save()

    # Rename existing 'Moderators' to 'Publishing Officers'
    moderators_group = Group.objects.get(name="Moderators")
    moderators_group.name = settings.PUBLISHING_OFFICERS_GROUP_NAME
    moderators_group.save()

    # Delete existing 'Editors' group if it exists
    try:
        editors_group = Group.objects.get(name="Editors")
        editors_group.delete()
    except Group.DoesNotExist:
        pass


class Migration(migrations.Migration):
    dependencies = [
        ("wagtailadmin", "0001_create_admin_access_permissions"),  # Ensure this migration runs after Wagtail's setup
        ("core", "0003_delete_tracking"),
    ]

    operations = [
        migrations.RunPython(update_user_groups),
    ]
