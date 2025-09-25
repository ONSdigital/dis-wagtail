from django.conf import settings
from django.db import migrations


def create_welsh_homepage(apps, schema_editor):
    # Get models
    ContentType = apps.get_model("contenttypes.ContentType")
    Page = apps.get_model("wagtailcore.Page")
    HomePage = apps.get_model("home.HomePage")
    Locale = apps.get_model("wagtailcore", "Locale")

    welsh_locale = Locale.objects.get(language_code="cy")
    if HomePage.objects.filter(url_path="/home-cy/", locale=welsh_locale).exists():
        return

    homepage_content_type, created = ContentType.objects.get_or_create(model="homepage", app_label="home")

    root_page = Page.objects.get(depth=1)
    default_homepage = HomePage.objects.first()

    HomePage.objects.create(
        title="Home",
        draft_title="Home",
        slug="home-cy",
        content_type=homepage_content_type,
        alias_of=default_homepage,
        translation_key=default_homepage.translation_key,
        locale=welsh_locale,
        path=f"{root_page.path}00{root_page.numchild + 1:02d}",
        depth=2,
        numchild=0,
        url_path="/home-cy/",
    )
    root_page.numchild += 1
    root_page.save()


def _get_default_hostnames_by_country_code() -> dict[str, str]:
    return {settings.CMS_HOSTNAME_LOCALE_MAP[host]: host for host in settings.CMS_HOSTNAME_ALTERNATIVES}


def update_english_site_entry(apps, schema_editor):
    Site = apps.get_model("wagtailcore.Site")

    default_hostname = _get_default_hostnames_by_country_code().get(settings.LANGUAGE_CODE, "ons.gov.uk")
    default_site = Site.objects.get(is_default_site=True)

    update_fields = []
    if default_site.hostname != default_hostname:
        default_site.hostname = default_hostname
        update_fields.append("hostname")

    if default_site.port != 443:  # noqa: PLR2004
        default_site.port = 443
        update_fields.append("port")

    if update_fields:
        default_site.save(update_fields=update_fields)


def create_welsh_site_entry(apps, schema_editor):
    Site = apps.get_model("wagtailcore.Site")
    HomePage = apps.get_model("home.HomePage")

    welsh_home = HomePage.objects.get(locale__language_code="cy")
    # Create a site with the new homepage set as the root
    if not Site.objects.filter(root_page=welsh_home).exists():
        hostname = _get_default_hostnames_by_country_code().get("cy", "cy.ons.gov.uk")
        Site.objects.create(
            hostname=hostname,
            root_page=welsh_home,
            port=443,
            site_name="Swyddfa Ystadegau Gwladol",
            is_default_site=False,
        )


class Migration(migrations.Migration):
    dependencies = [("core", "0007_remove_glossaryterm_core_glossary_term_name_unique_and_more")]

    operations = [
        migrations.RunPython(create_welsh_homepage, migrations.RunPython.noop),
        migrations.RunPython(create_welsh_site_entry, migrations.RunPython.noop),
        migrations.RunPython(update_english_site_entry, migrations.RunPython.noop),
    ]
