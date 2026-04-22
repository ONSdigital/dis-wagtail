from django.conf import settings
from django.db import migrations

DELETE_CODENAMES = ("bulk_delete_page",)


def add_publishing_officers_delete_permissions(apps, schema_editor):
    """Grant bulk_delete_page permission to Publishing Officers so they can delete pages
    with descendants.
    """
    Page = apps.get_model("wagtailcore.Page")
    Group = apps.get_model("auth.Group")
    Permission = apps.get_model("auth.Permission")
    GroupPagePermission = apps.get_model("wagtailcore.GroupPagePermission")

    root_page = Page.objects.get(depth=1)
    group = Group.objects.get(name=settings.PUBLISHING_OFFICERS_GROUP_NAME)

    for codename in DELETE_CODENAMES:
        permission = Permission.objects.get(codename=codename)
        if not GroupPagePermission.objects.filter(group=group, page=root_page, permission=permission).exists():
            GroupPagePermission.objects.create(group=group, page=root_page, permission=permission)


def remove_publishing_officers_delete_permissions(apps, schema_editor):
    """Remove bulk_delete_page permission from Publishing Officers."""
    Page = apps.get_model("wagtailcore.Page")
    Group = apps.get_model("auth.Group")
    Permission = apps.get_model("auth.Permission")
    GroupPagePermission = apps.get_model("wagtailcore.GroupPagePermission")

    root_page = Page.objects.get(depth=1)
    group = Group.objects.get(name=settings.PUBLISHING_OFFICERS_GROUP_NAME)

    for codename in DELETE_CODENAMES:
        permission = Permission.objects.get(codename=codename)
        GroupPagePermission.objects.filter(group=group, page=root_page, permission=permission).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0015_delete_existing_page_view_restrictions"),
    ]

    operations = [
        migrations.RunPython(
            add_publishing_officers_delete_permissions,
            remove_publishing_officers_delete_permissions,
        ),
    ]
