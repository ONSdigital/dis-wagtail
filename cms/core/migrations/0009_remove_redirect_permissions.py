from django.conf import settings
from django.db import migrations


def remove_redirect_permissions(apps, schema_editor):
    """Remove redirect permissions from Publishing Admins group.

    This ensures only superusers can manage redirects, preventing
    non-technical editors from modifying site routing unintentionally.
    """
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    try:
        publishing_admins = Group.objects.get(name=settings.PUBLISHING_ADMINS_GROUP_NAME)

        # Find all redirect-related permissions
        redirect_permissions = Permission.objects.filter(
            content_type__app_label="wagtailredirects", content_type__model="redirect"
        )

        # Remove each permission from the Publishing Admins group
        for permission in redirect_permissions:
            publishing_admins.permissions.remove(permission)

    except Group.DoesNotExist:
        pass


def restore_redirect_permissions(apps, schema_editor):
    """Restore redirect permissions to Publishing Admins group (for rollback).

    This is the reverse operation that re-grants redirect management
    permissions if the migration needs to be rolled back.
    """
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    PERMISSION_TYPES = ["add", "change", "delete"]

    try:
        publishing_admins = Group.objects.get(name=settings.PUBLISHING_ADMINS_GROUP_NAME)

        # Get the redirect model's content type
        redirect_model = apps.get_model("wagtailredirects", "Redirect")
        content_type = ContentType.objects.get_for_model(redirect_model)

        # Re-add each permission type
        for permission_type in PERMISSION_TYPES:
            permission, created = Permission.objects.get_or_create(
                content_type=content_type,
                codename=f"{permission_type}_redirect",
                defaults={"name": f"Can {permission_type} redirect"},
            )
            publishing_admins.permissions.add(permission)

    except Group.DoesNotExist:
        pass


class Migration(migrations.Migration):
    """Remove redirect management permissions from Publishing Admins.

    This migration restricts Wagtail redirect management to superusers only,
    removing the permissions previously granted to Publishing Admins in
    migration 0006_update_user_groups.

    Rationale: Redirects directly affect site navigation, SEO, and content
    accessibility. Limiting this to superusers reduces risk of misconfigurations.
    """

    dependencies = [
        ("core", "0008_delete_systemmessagessettings"),
        ("wagtailredirects", "0008_add_verbose_name_plural"),  # Ensure redirect app is ready
    ]

    operations = [
        migrations.RunPython(
            remove_redirect_permissions,
            restore_redirect_permissions,
        ),
    ]
