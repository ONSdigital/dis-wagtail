import uuid

from django.db import migrations


def create_default_menus(apps, schema_editor):
    """Create default MainMenu and FooterMenu (as drafts), and configure NavigationSettings."""
    MainMenu = apps.get_model("navigation", "MainMenu")
    FooterMenu = apps.get_model("navigation", "FooterMenu")
    NavigationSettings = apps.get_model("navigation", "NavigationSettings")
    Locale = apps.get_model("wagtailcore", "Locale")
    Site = apps.get_model("wagtailcore", "Site")

    # Get default locale
    english_locale = Locale.objects.get(language_code="en-gb")

    # Create MainMenu if it doesn't exist for default locale
    main_menu, _ = MainMenu.objects.get_or_create(
        locale=english_locale,
        defaults={
            "translation_key": uuid.uuid4(),
            "highlights": "[]",
            "columns": "[]",
        },
    )

    # Create FooterMenu if it doesn't exist for default locale
    footer_menu, _ = FooterMenu.objects.get_or_create(
        locale=english_locale,
        defaults={
            "translation_key": uuid.uuid4(),
            "columns": "[]",
        },
    )

    # Configure NavigationSettings for the default site
    default_site = Site.objects.filter(is_default_site=True).first()
    if not default_site:
        default_site = Site.objects.first()

    if default_site:
        nav_settings, _ = NavigationSettings.objects.get_or_create(site=default_site)
        if nav_settings.main_menu is None:
            nav_settings.main_menu = main_menu
        if nav_settings.footer_menu is None:
            nav_settings.footer_menu = footer_menu
        nav_settings.save()


class Migration(migrations.Migration):
    dependencies = [
        ("navigation", "0004_update_publishing_admin_permissions"),
    ]

    operations = [
        migrations.RunPython(create_default_menus, reverse_code=migrations.RunPython.noop),
    ]
