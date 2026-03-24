from django.db import migrations


def create_welsh_menus(apps, schema_editor):
    """Create MainMenu and FooterMenu (as drafts) for the Welsh locale,
    and configure NavigationSettings for the Welsh site.
    """
    MainMenu = apps.get_model("navigation", "MainMenu")
    FooterMenu = apps.get_model("navigation", "FooterMenu")
    NavigationSettings = apps.get_model("navigation", "NavigationSettings")
    Locale = apps.get_model("wagtailcore", "Locale")
    Site = apps.get_model("wagtailcore", "Site")

    # Get Welsh locale
    welsh_locale = Locale.objects.get(language_code="cy")

    # Get Welsh locale
    english_locale = Locale.objects.get(language_code="en-gb")

    # Reuse the English menu's translation_key so Wagtail links them as translations
    english_main_menu = MainMenu.objects.get(locale=english_locale)
    english_footer_menu = FooterMenu.objects.get(locale=english_locale)

    # Create MainMenu if it doesn't exist for Welsh locale
    main_menu, _ = MainMenu.objects.get_or_create(
        locale=welsh_locale,
        defaults={
            "translation_key": english_main_menu.translation_key,
            "highlights": "[]",
            "columns": "[]",
        },
    )

    # Create FooterMenu if it doesn't exist for Welsh locale
    footer_menu, _ = FooterMenu.objects.get_or_create(
        locale=welsh_locale,
        defaults={
            "translation_key": english_footer_menu.translation_key,
            "columns": "[]",
        },
    )

    welsh_site = Site.objects.filter(root_page__locale=welsh_locale).first()

    nav_settings, _ = NavigationSettings.objects.get_or_create(site=welsh_site)
    if nav_settings.main_menu is None:
        nav_settings.main_menu = main_menu
    if nav_settings.footer_menu is None:
        nav_settings.footer_menu = footer_menu
    nav_settings.save()


class Migration(migrations.Migration):
    dependencies = [
        ("navigation", "0005_create_default_menus"),
    ]

    operations = [
        migrations.RunPython(create_welsh_menus, reverse_code=migrations.RunPython.noop),
    ]
