from django.conf import settings
from django.db import migrations


def create_access_unpublished_permission(apps, schema_editor):
    ContentType = apps.get_model("contenttypes.ContentType")
    Permission = apps.get_model("auth.Permission")
    Group = apps.get_model("auth.Group")

    model_class = apps.get_model("datasets.Dataset")
    content_type = ContentType.objects.get_for_model(model_class)
    permission, _was_created = Permission.objects.get_or_create(
        content_type=content_type,
        codename="access_unpublished_datasets",
        defaults={"name": "Can access unpublished datasets"},
    )

    admins_group = Group.objects.get(name=settings.PUBLISHING_ADMINS_GROUP_NAME)
    officers_group = Group.objects.get(name=settings.PUBLISHING_OFFICERS_GROUP_NAME)

    admins_group.permissions.add(permission)
    officers_group.permissions.add(permission)


class Migration(migrations.Migration):
    dependencies = [
        ("datasets", "0002_alter_dataset_version"),
    ]

    operations = [
        migrations.RunPython(
            create_access_unpublished_permission,
            reverse_code=migrations.RunPython.noop,
            elidable=True,
        ),
    ]
