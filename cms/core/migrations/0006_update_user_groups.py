from django.conf import settings
from django.db import migrations
from wagtail.models import PAGE_PERMISSION_CODENAMES, GroupCollectionPermission, GroupPagePermission

WAGTAIL_PERMISSION_TYPES = ["add", "change", "delete"]

WAGTAIL_PAGE_PERMISSION_TYPES = [codename.replace("_page", "") for codename in PAGE_PERMISSION_CODENAMES]


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


def create_user_groups(apps):
    """Remove the existing Wagtail user groups and create new ones,
    and give them  the "Access the Wagtail admin" permission.
    """
    Group = apps.get_model("auth.Group")

    # Remove existing Wagtail groups
    for wagtail_group in Group.objects.all():
        wagtail_group.delete()

    # Create the Publishing Admin, Publishing Officer and Viewer groups and give them the 'access_admin' permission
    for group_name in [
        settings.PUBLISHING_ADMINS_GROUP_NAME,
        settings.PUBLISHING_OFFICERS_GROUP_NAME,
        settings.VIEWERS_GROUP_NAME,
    ]:
        Group.objects.create(name=group_name)
        assign_permission_to_group(apps, group_name, "access_admin", "wagtailadmin", "admin")


def create_reporting_permissions(apps):
    """Allow Publishing Admins to view the log entry reports."""
    # The "Reports" section and everything under it
    assign_permission_to_group(
        apps, settings.PUBLISHING_ADMINS_GROUP_NAME, "view_logentry", "wagtailcore", "PageLogEntry"
    )


def create_image_permissions(apps):
    """Allow Publishing Admins to add and edit images in the image library.
    Note that the 'choose_image' permission isn't required
    as it's assigned to all users which have the "Access the Wagtail admin" permission.
    See: https://github.com/wagtail/wagtail/blob/125a749a9ab785757dd898e2f88bfb8fd3f65e11/wagtail/images/migrations/0023_add_choose_permissions.py#L23.
    """
    # TODO:  these shouldn't be imported directly and should be using historical models instead
    # Group = apps.get_model("auth.Group")
    # Permission = apps.get_model("auth.Permission")
    # Collection = apps.get_model("wagtailcore.Collection")
    from django.contrib.auth.models import Group, Permission
    from wagtail.models import Collection

    group = Group.objects.get(name=settings.PUBLISHING_ADMINS_GROUP_NAME)
    root_collection = Collection.get_first_root_node()

    GroupCollectionPermission.objects.create(
        group=group,
        collection=root_collection,
        permission=Permission.objects.get(content_type__app_label="wagtailimages", codename="add_image"),
    )
    GroupCollectionPermission.objects.create(
        group=group,
        collection=root_collection,
        permission=Permission.objects.get(content_type__app_label="wagtailimages", codename="change_image"),
    )


def create_snippet_permissions(apps):
    """Allow Publishing Admins to create, edit and delete snippets."""
    snippet_classes_dict = {
        "GlossaryTerm": "core",
        "ContactDetails": "core",
        "MainMenu": "navigation",
        "FooterMenu": "navigation",
    }

    for model, app in snippet_classes_dict.items():
        for permission in WAGTAIL_PERMISSION_TYPES:
            assign_permission_to_group(
                apps,
                settings.PUBLISHING_ADMINS_GROUP_NAME,
                permission_codename=f"{permission}_{model.lower()}",
                app=app,
                model=model,
            )
        if model in ("MainMenu", "FooterMenu"):
            # MainMenu and FooterMenu are publishable
            assign_permission_to_group(
                apps,
                settings.PUBLISHING_ADMINS_GROUP_NAME,
                permission_codename=f"publish_{model.lower()}",
                app=app,
                model=model,
            )


def create_bundle_permissions(apps):
    """Grant all permissions on Bundles to Publishing Admins and Publishing Officers,
    and view-only access to Viewers.
    """
    bundles_app = "bundles"
    bundle_class = "Bundle"

    for permission in WAGTAIL_PERMISSION_TYPES:
        for group_name in [settings.PUBLISHING_ADMINS_GROUP_NAME, settings.PUBLISHING_OFFICERS_GROUP_NAME]:
            assign_permission_to_group(
                apps,
                group_name=group_name,
                permission_codename=f"{permission}_{bundle_class.lower()}",
                app=bundles_app,
                model=bundle_class,
            )

    # View-only access for the Viewers group
    assign_permission_to_group(apps, settings.VIEWERS_GROUP_NAME, "view_bundle", bundles_app, bundle_class)


def create_page_permissions(apps):
    """Allow Publishing Admins and Publishing Officers all permissions on the HomePage and its children."""
    # TODO: these shouldn't be imported directly and should use historical models instead
    from django.contrib.auth.models import Group

    from cms.home.models import HomePage

    # HomePage = apps.get_model("home.HomePage")
    # Group = apps.get_model("auth.Group")

    home_page = HomePage.objects.first()

    for group_name in [settings.PUBLISHING_ADMINS_GROUP_NAME, settings.PUBLISHING_OFFICERS_GROUP_NAME]:
        group = Group.objects.get(name=group_name)
        for permission_type in WAGTAIL_PAGE_PERMISSION_TYPES:
            GroupPagePermission.objects.create(group=group, page=home_page, permission_type=permission_type)


def create_topic_page_featured_series_permission(apps):
    """Create a custom permission that will be registered using a Wagtail hook,
    given to the Publishing Admins group,
    and used on the TopicPage's featured article series FieldPanel.
    """
    assign_permission_to_group(
        apps,
        group_name=settings.PUBLISHING_ADMINS_GROUP_NAME,
        permission_codename="add_featured_article_series_on_topic_page",
        app="wagtailadmin",
        model="admin",
    )


def update_user_groups(apps, schema_editor):
    """Create user groups for the CMS."""
    create_user_groups(apps)
    create_page_permissions(apps)
    create_image_permissions(apps)
    create_snippet_permissions(apps)
    create_bundle_permissions(apps)
    create_reporting_permissions(apps)
    create_topic_page_featured_series_permission(apps)


class Migration(migrations.Migration):
    dependencies = [
        # Wagtail dependencies
        ("wagtailadmin", "0005_editingsession_is_editing"),  # latest Wagtail admin migration
        ("wagtailcore", "0094_alter_page_locale"),  # latest Wagtail core migration
        ("wagtailimages", "0027_image_description"),  # latest Wagtail images migration
        # CMS dependencies
        ("core", "0005_glossaryterm"),  # Snippets in the 'core' app
        ("home", "0002_create_homepage"),  # HomePage
        ("topics", "0002_featured_series_explore_more_related"),  # Featured article series on TopicPage
        ("navigation", "0002_footermenu_navigationsettings_footer_menu"),  # MainMenu and FooterMenu
        ("bundles", "0001_initial"),  # Bundles
    ]

    operations = [
        migrations.RunPython(update_user_groups),
    ]
