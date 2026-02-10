from django.conf import settings
from django.db import migrations


def update_publishing_admin_permissions(apps, schema_editor):
    """Remove NavigationSettings change permission and add translation permission
    for Publishing Admins group.
    """
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    publishing_admins = Group.objects.get(name=settings.PUBLISHING_ADMINS_GROUP_NAME)

    # Remove change_navigationsettings permission
    navigation_settings = apps.get_model("navigation", "NavigationSettings")
    nav_settings_ct = ContentType.objects.get_for_model(navigation_settings)
    change_nav_perm = Permission.objects.get(
        content_type=nav_settings_ct,
        codename="change_navigationsettings",
    )
    publishing_admins.permissions.remove(change_nav_perm)

    # Add submit_translation permission
    submit_translation_perm = Permission.objects.get(codename="submit_translation")
    publishing_admins.permissions.add(submit_translation_perm)


def reverse_update_publishing_admin_permissions(apps, schema_editor):
    """Reverse the permission changes."""
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    publishing_admins = Group.objects.get(name=settings.PUBLISHING_ADMINS_GROUP_NAME)

    # Re-add change_navigationsettings permission
    navigation_settings = apps.get_model("navigation", "NavigationSettings")
    nav_settings_ct = ContentType.objects.get_for_model(navigation_settings)
    change_nav_perm = Permission.objects.get(
        content_type=nav_settings_ct,
        codename="change_navigationsettings",
    )
    publishing_admins.permissions.add(change_nav_perm)

    # Remove submit_translation permission
    submit_translation_perm = Permission.objects.get(codename="submit_translation")
    publishing_admins.permissions.remove(submit_translation_perm)


class Migration(migrations.Migration):
    dependencies = [
        ("navigation", "0003_footermenu_locale_footermenu_translation_key_and_more"),  # The previous migration
    ]

    operations = [
        migrations.RunPython(
            update_publishing_admin_permissions,
            reverse_update_publishing_admin_permissions,
        ),
    ]
