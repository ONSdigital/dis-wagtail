from django.conf import settings
from django.db import migrations


def add_publishing_officers_publish_permission(apps, schema_editor):
    """Grant the publish pages permission. BasePagePermissionTester extends this."""
    Page = apps.get_model("wagtailcore.Page")
    Group = apps.get_model("auth.Group")
    Permission = apps.get_model("auth.Permission")
    GroupPagePermission = apps.get_model("wagtailcore.GroupPagePermission")

    root_page = Page.objects.get(depth=1)

    group = Group.objects.get(name=settings.PUBLISHING_OFFICERS_GROUP_NAME)
    permission = Permission.objects.get(codename="publish_page")
    GroupPagePermission.objects.create(group=group, page=root_page, permission=permission)


def remove_publishing_officers_publish_permission(apps, schema_editor):
    """Remove the publish page permission."""
    Page = apps.get_model("wagtailcore.Page")
    Group = apps.get_model("auth.Group")
    Permission = apps.get_model("auth.Permission")
    GroupPagePermission = apps.get_model("wagtailcore.GroupPagePermission")

    root_page = Page.objects.get(depth=1)

    group = Group.objects.get(name=settings.PUBLISHING_OFFICERS_GROUP_NAME)
    permission = Permission.objects.get(codename="publish_page")
    GroupPagePermission.objects.filter(group=group, page=root_page, permission=permission).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0011_migrate_imageblock_caption"),
    ]

    operations = [
        migrations.RunPython(add_publishing_officers_publish_permission, remove_publishing_officers_publish_permission),
    ]
