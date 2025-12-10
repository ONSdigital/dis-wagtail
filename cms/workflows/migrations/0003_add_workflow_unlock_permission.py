from django.conf import settings
from django.db import migrations


def create_unlock_workflow_tasks_permission(apps, schema_editor):
    ContentType = apps.get_model("contenttypes.ContentType")
    AdminModel = apps.get_model("wagtailadmin.Admin")
    Permission = apps.get_model("auth.Permission")
    Group = apps.get_model("auth.Group")

    unlock_permission, _ = Permission.objects.get_or_create(
        content_type=ContentType.objects.get_for_model(AdminModel),
        codename="unlock_workflow_tasks",
        name="Unlock any manually locked workflow task",
    )

    publishing_admins = Group.objects.get(name=settings.PUBLISHING_ADMINS_GROUP_NAME)
    publishing_admins.permissions.add(unlock_permission)


def remove_unlock_workflow_tasks_permission(apps, schema_editor):
    ContentType = apps.get_model("contenttypes.ContentType")
    AdminModel = apps.get_model("wagtailadmin.Admin")
    Permission = apps.get_model("auth.Permission")

    # this cascades to groups
    Permission.objects.filter(
        content_type=ContentType.objects.get_for_model(AdminModel),
        codename="unlock_workflow_tasks",
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("workflows", "0002_review_workflow")]

    operations = [
        migrations.RunPython(create_unlock_workflow_tasks_permission, remove_unlock_workflow_tasks_permission),
    ]
