from django.conf import settings
from django.db import migrations

WAGTAIL_PERMISSION_TYPES = ["add", "change", "delete"]

WAGTAIL_PAGE_PERMISSION_TYPES = ["add", "change", "bulk_delete", "lock", "publish", "unlock"]


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


def create_user_groups(apps):
    """Remove the existing Wagtail user groups and create new ones,
    and give them  the "Access the Wagtail admin" permission.
    """
    Group = apps.get_model("auth.Group")

    # Remove all existing Wagtail groups
    Group.objects.all().delete()

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


def create_collection_permissions(apps):
    """Grant Publishing Admins full permissions on the root collections for images and documents,
    and allow Publishing Officers to select images and documents for use on pages.
    """
    Group = apps.get_model("auth.Group")
    Permission = apps.get_model("auth.Permission")
    Collection = apps.get_model("wagtailcore.Collection")
    GroupCollectionPermission = apps.get_model("wagtailcore.GroupCollectionPermission")

    root_collection = Collection.objects.get(depth=1)

    collection_classes = [
        # app_label, model
        ("wagtailimages", "image"),
        ("wagtaildocs", "document"),
    ]

    # Grant add, change and delete permissions to Publishing Admins
    for permission in WAGTAIL_PERMISSION_TYPES:
        for app, model in collection_classes:
            GroupCollectionPermission.objects.create(
                group=Group.objects.get(name=settings.PUBLISHING_ADMINS_GROUP_NAME),
                collection=root_collection,
                permission=Permission.objects.get(content_type__app_label=app, codename=f"{permission}_{model}"),
            )

    # Grant "choose" permission to Publishing Admins and Publishing Officers
    for group_name in [settings.PUBLISHING_ADMINS_GROUP_NAME, settings.PUBLISHING_OFFICERS_GROUP_NAME]:
        for app, model in collection_classes:
            GroupCollectionPermission.objects.create(
                group=Group.objects.get(name=group_name),
                collection=root_collection,
                permission=Permission.objects.get(content_type__app_label=app, codename=f"choose_{model}"),
            )


def create_snippet_permissions(apps):
    """Allow Publishing Admins to create, edit and delete snippets."""
    snippet_classes = [
        # app, model, add publish permission
        ("core", "GlossaryTerm", False),
        ("core", "ContactDetails", False),
        ("navigation", "MainMenu", True),
        ("navigation", "FooterMenu", True),
    ]

    for app, model, add_publish_permission in snippet_classes:
        for permission in WAGTAIL_PERMISSION_TYPES:
            assign_permission_to_group(
                apps,
                settings.PUBLISHING_ADMINS_GROUP_NAME,
                permission_codename=f"{permission}_{model.lower()}",
                app=app,
                model=model,
            )
        if add_publish_permission:
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

    # Allow all users to view the bundles
    for group_name in [
        settings.PUBLISHING_ADMINS_GROUP_NAME,
        settings.PUBLISHING_OFFICERS_GROUP_NAME,
        settings.VIEWERS_GROUP_NAME,
    ]:
        assign_permission_to_group(apps, group_name, "view_bundle", bundles_app, bundle_class)

    # Allow PAs and POs to manage the bundles
    for permission in WAGTAIL_PERMISSION_TYPES:
        for group_name in [settings.PUBLISHING_ADMINS_GROUP_NAME, settings.PUBLISHING_OFFICERS_GROUP_NAME]:
            assign_permission_to_group(
                apps,
                group_name=group_name,
                permission_codename=f"{permission}_{bundle_class.lower()}",
                app=bundles_app,
                model=bundle_class,
            )


def create_page_permissions(apps):
    """Grant Publishing Admins full permissions on the root page and all its subpages.
    Allow Publishing Officers to add, edit and delete unpublished pages.
    """
    Page = apps.get_model("wagtailcore.Page")
    Group = apps.get_model("auth.Group")
    Permission = apps.get_model("auth.Permission")

    GroupPagePermission = apps.get_model("wagtailcore.GroupPagePermission")

    root_page = Page.objects.get(depth=1)

    for group_name in [settings.PUBLISHING_ADMINS_GROUP_NAME, settings.PUBLISHING_OFFICERS_GROUP_NAME]:
        group = Group.objects.get(name=group_name)
        for type in WAGTAIL_PAGE_PERMISSION_TYPES:
            if group_name == settings.PUBLISHING_OFFICERS_GROUP_NAME and type not in ("add", "change"):
                continue  # Only allow Publishing Officers to add and change pages

            permission = Permission.objects.get(codename=f"{type}_page")

            GroupPagePermission.objects.create(group=group, page=root_page, permission=permission)


def create_team_permissions(apps):
    """Grant Publishing Admins and Publishing Officers view Preview Teams permission."""
    for group_name in [settings.PUBLISHING_ADMINS_GROUP_NAME, settings.PUBLISHING_OFFICERS_GROUP_NAME]:
        assign_permission_to_group(
            apps,
            group_name=group_name,
            permission_codename="view_team",
            app="teams",
            model="team",
        )


def create_settings_permissions(apps):
    """Allow Publishing Admins to edit Wagtail settings."""
    # Redirect
    for permission in WAGTAIL_PERMISSION_TYPES:
        assign_permission_to_group(
            apps,
            group_name=settings.PUBLISHING_ADMINS_GROUP_NAME,
            permission_codename=f"{permission}_redirect",
            app="wagtailredirects",
            model="redirect",
        )

    # Navigation Settings
    assign_permission_to_group(
        apps,
        group_name=settings.PUBLISHING_ADMINS_GROUP_NAME,
        permission_codename="change_navigationsettings",
        app="navigation",
        model="navigationsettings",
    )

    # Social Media Settings
    assign_permission_to_group(
        apps,
        group_name=settings.PUBLISHING_ADMINS_GROUP_NAME,
        permission_codename="change_socialmediasettings",
        app="core",
        model="socialmediasettings",
    )


def update_user_groups(apps, schema_editor):
    """Create user groups for the CMS."""
    create_user_groups(apps)
    create_page_permissions(apps)
    create_collection_permissions(apps)
    create_snippet_permissions(apps)
    create_bundle_permissions(apps)
    create_team_permissions(apps)
    create_settings_permissions(apps)
    create_reporting_permissions(apps)


class Migration(migrations.Migration):
    dependencies = [
        # Wagtail dependencies
        ("wagtailadmin", "0005_editingsession_is_editing"),  # latest Wagtail admin migration
        ("wagtailcore", "0094_alter_page_locale"),  # latest Wagtail core migration
        ("wagtailimages", "0027_image_description"),  # latest Wagtail images migration
        ("wagtaildocs", "0014_alter_document_file_size"),  # latest Wagtail documents migration
        ("wagtailredirects", "0008_add_verbose_name_plural"),  # latest Wagtail redirects migration
        # CMS dependencies
        ("core", "0005_glossaryterm"),  # Snippets in the 'core' app
        ("home", "0002_create_homepage"),  # HomePage
        ("topics", "0002_featured_series_explore_more_related"),  # Featured article series on TopicPage
        ("navigation", "0002_footermenu_navigationsettings_footer_menu"),  # MainMenu and FooterMenu
        ("bundles", "0001_initial"),  # Bundles
        ("teams", "0001_initial"),  # Teams
    ]

    operations = [
        migrations.RunPython(update_user_groups, migrations.RunPython.noop),
    ]
