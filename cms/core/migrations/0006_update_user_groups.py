import contextlib

from django.conf import settings
from django.db import migrations
from wagtail.models import GroupPagePermission


def create_user_groups(apps):
    ContentType = apps.get_model("contenttypes.ContentType")
    Permission = apps.get_model("auth.Permission")
    Group = apps.get_model("auth.Group")

    # Remove existing Wagtail groups
    for wagtail_group in Group.objects.all():
        with contextlib.suppress(Group.DoesNotExist):
            wagtail_group.delete()

    # Get the 'access_admin' permission and assign to the new groups
    wagtailadmin_content_type = ContentType.objects.get(
        app_label="wagtailadmin",
        model="admin",
    )
    access_admin_permission = Permission.objects.get(content_type=wagtailadmin_content_type, codename="access_admin")

    # Create the Publishing Admin, Publishing Officer and Viewer groups and give them the 'access_admin' permission
    for group_name in [
        settings.PUBLISHING_ADMINS_GROUP_NAME,
        settings.PUBLISHING_OFFICERS_GROUP_NAME,
        settings.VIEWERS_GROUP_NAME,
    ]:
        group, _was_created = Group.objects.get_or_create(name=group_name)
        group.permissions.add(access_admin_permission)
        group.save()


def assign_permission_to_group(apps, group_name, permission_codename, app, model):
    """Helper method to assign a permission to a group."""
    ContentType = apps.get_model("contenttypes.ContentType")
    Permission = apps.get_model("auth.Permission")
    Group = apps.get_model("auth.Group")

    model_class = apps.get_model(f"{app}.{model}")
    content_type = ContentType.objects.get_for_model(model_class)
    permission, _was_created = Permission.objects.get_or_create(
        content_type=content_type,
        codename=permission_codename,
        defaults={"name": f"Can {' '.join(permission_codename.split('_'))}"},
    )
    group = Group.objects.get(name=group_name)

    group.permissions.add(permission)
    group.save()


def create_reporting_permissions(apps):
    """Allow Publishing Admins to view the log entry reports."""
    # The "Reports" section and everything under it
    assign_permission_to_group(
        apps, settings.PUBLISHING_ADMINS_GROUP_NAME, "view_logentry", "wagtailcore", "PageLogEntry"
    )


def create_snippet_permissions(apps):
    """Allow admin users to create, edit and delete snippets."""
    snippet_classes_dict = {
        "GlossaryTerm": "core",
        "ContactDetails": "core",
        "MainMenu": "navigation",
        "FooterMenu": "navigation",
    }
    PERMISSIONS = [
        "add_",
        "change_",
        "delete_",
        "view_",
    ]
    for model, app in snippet_classes_dict.items():
        for permission in PERMISSIONS:
            assign_permission_to_group(
                apps,
                settings.PUBLISHING_ADMINS_GROUP_NAME,
                permission_codename=f"{permission}{model.lower()}",
                app=app,
                model=model,
            )


def create_bundle_permissions(apps):
    PERMISSIONS = [
        "add_",
        "change_",
        "delete_",
        "view_",
    ]

    bundles_app = "bundles"
    bundle_class = "Bundle"
    bundle_page_class = "BundlePage"

    for permission in PERMISSIONS:
        for group_name in [settings.PUBLISHING_ADMINS_GROUP_NAME, settings.PUBLISHING_OFFICERS_GROUP_NAME]:
            assign_permission_to_group(
                apps,
                group_name=group_name,
                permission_codename=f"{permission}{bundle_class.lower()}",
                app=bundles_app,
                model=bundle_class,
            )
            assign_permission_to_group(
                apps,
                group_name=group_name,
                permission_codename=f"{permission}{bundle_page_class.lower()}",
                app=bundles_app,
                model=bundle_page_class,
            )

    # Explicitly allow Viewers to view Bundles and their pages
    assign_permission_to_group(apps, settings.VIEWERS_GROUP_NAME, "view_bundle", "bundles", "Bundle")
    assign_permission_to_group(apps, settings.VIEWERS_GROUP_NAME, "view_bundlepage", "bundles", "BundlePage")


def create_page_permissions(apps):
    """Allow Publishing Admins and Publishing Officers all permissions on the HomePage and its children."""
    # Taken from: https://github.com/wagtail/wagtail/blob/8f640a8cdb0dfcf14e611d33cbff388d5db7cf9d/wagtail/models/pages.py#L264
    PERMISSION_TYPES = [
        "add",
        "bulk_delete",
        "change",
        "lock",
        "publish",
        "unlock",
    ]

    # TODO: these shouldn't be imported
    from django.contrib.auth.models import Group

    from cms.home.models import HomePage

    # HomePage = apps.get_model("home.HomePage")
    # Group = apps.get_model("auth.Group")

    home_page = HomePage.objects.first()

    for group_name in [settings.PUBLISHING_ADMINS_GROUP_NAME, settings.PUBLISHING_OFFICERS_GROUP_NAME]:
        group = Group.objects.get(name=group_name)
        for permission_type in PERMISSION_TYPES:
            GroupPagePermission.objects.create(group=group, page=home_page, permission_type=permission_type)


def create_topic_page_headline_figures_permissions(apps):
    """Create custom permission that will be used on the TopicPage's HeadlineFigures FieldPanel."""
    # assign_permission_to_group(
    #     apps,
    #     group_name=settings.PUBLISHING_ADMINS_GROUP_NAME,
    #     permission_codename="change_topicpage_headlinefigures",
    #     app="wagtailadmin",
    #     model="Admin",
    # )

    # Explicit steps from the above function for debugging

    ContentType = apps.get_model("contenttypes.ContentType")
    Permission = apps.get_model("auth.Permission")
    Group = apps.get_model("auth.Group")

    wagtailadmin_content_type = ContentType.objects.get(
        app_label="wagtailadmin",
        model="admin",
    )
    permission, _ = Permission.objects.get_or_create(
        content_type=wagtailadmin_content_type,
        codename="topicpage_headlinefigures_permission",
        defaults={"name": "Can change headline figures on topic page"},
    )

    group = Group.objects.get(name=settings.PUBLISHING_ADMINS_GROUP_NAME)
    group.permissions.add(permission)
    group.save()


def update_user_groups(apps, schema_editor):
    """Update the core user groups for the CMS."""
    create_user_groups(apps)
    create_page_permissions(apps)
    create_snippet_permissions(apps)
    create_bundle_permissions(apps)
    create_reporting_permissions(apps)
    create_topic_page_headline_figures_permissions(apps)


class Migration(migrations.Migration):
    dependencies = [
        ("wagtailadmin", "0001_create_admin_access_permissions"),  # Ensure this migration runs after Wagtail's setup
        ("core", "0005_glossaryterm"),
        ("home", "0002_create_homepage"),  # and HomePage exists
        ("navigation", "0002_footermenu_navigationsettings_footer_menu"),
        ("wagtailcore", "0094_alter_page_locale"),
    ]

    operations = [
        migrations.RunPython(update_user_groups),
    ]
