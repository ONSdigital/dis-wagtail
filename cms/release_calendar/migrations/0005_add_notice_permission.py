from django.conf import settings
from django.db import migrations


def create_notice_deletion_permissions(apps, schema_editor):
    ContentType = apps.get_model("contenttypes.ContentType")
    Permission = apps.get_model("auth.Permission")
    Group = apps.get_model("auth.Group")

    model_class = apps.get_model("release_calendar.ReleaseCalendarPage")
    content_type = ContentType.objects.get_for_model(model_class)
    permission, _was_created = Permission.objects.get_or_create(
        content_type=content_type,
        codename="modify_notice",
        defaults={"name": "Can modify notice"},
    )
    group = Group.objects.get(name=settings.PUBLISHING_ADMINS_GROUP_NAME)

    group.permissions.add(permission)


class Migration(migrations.Migration):
    dependencies = [
        ("release_calendar", "0004_make_release_date_mandatory_and_rename_next_release_text"),
    ]

    operations = [
        migrations.RunPython(
            create_notice_deletion_permissions,
            reverse_code=migrations.RunPython.noop,
            elidable=True,
        ),
    ]
