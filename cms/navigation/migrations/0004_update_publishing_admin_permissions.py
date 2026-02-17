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

    # Remove delete_mainmenu permission
    main_menu = apps.get_model("navigation", "MainMenu")
    main_menu_ct = ContentType.objects.get_for_model(main_menu)
    delete_main_menu_perm = Permission.objects.get(
        content_type=main_menu_ct,
        codename="delete_mainmenu",
    )
    publishing_admins.permissions.remove(delete_main_menu_perm)

    # Remove delete_footermenu permission
    footer_menu = apps.get_model("navigation", "FooterMenu")
    footer_menu_ct = ContentType.objects.get_for_model(footer_menu)
    delete_footer_menu_perm = Permission.objects.get(
        content_type=footer_menu_ct,
        codename="delete_footermenu",
    )
    publishing_admins.permissions.remove(delete_footer_menu_perm)

    # Add submit_translation permission - create if it doesn't exist
    translation_ct, _ = ContentType.objects.get_or_create(
        app_label="simple_translation",
        model="simpletranslation",
    )
    submit_translation_perm, _ = Permission.objects.get_or_create(
        content_type=translation_ct,
        codename="submit_translation",
        defaults={"name": "Can submit translations"},
    )
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

    # Re-add delete_mainmenu permission
    main_menu = apps.get_model("navigation", "MainMenu")
    main_menu_ct = ContentType.objects.get_for_model(main_menu)
    delete_main_menu_perm = Permission.objects.get(
        content_type=main_menu_ct,
        codename="delete_mainmenu",
    )
    publishing_admins.permissions.add(delete_main_menu_perm)

    # Re-add delete_footermenu permission
    footer_menu = apps.get_model("navigation", "FooterMenu")
    footer_menu_ct = ContentType.objects.get_for_model(footer_menu)
    delete_footer_menu_perm = Permission.objects.get(
        content_type=footer_menu_ct,
        codename="delete_footermenu",
    )
    publishing_admins.permissions.add(delete_footer_menu_perm)

    # Remove submit_translation permission
    submit_translation_perm = Permission.objects.get(codename="submit_translation")
    publishing_admins.permissions.remove(submit_translation_perm)


class Migration(migrations.Migration):
    dependencies = [
        ("navigation", "0003_footermenu_locale_footermenu_translation_key_and_more"),
    ]

    operations = [
        migrations.RunPython(
            update_publishing_admin_permissions,
            reverse_update_publishing_admin_permissions,
        ),
    ]
