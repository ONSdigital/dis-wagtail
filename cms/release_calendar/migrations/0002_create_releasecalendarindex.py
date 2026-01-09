from django.db import migrations
from django.utils import timezone


def create_index_page(apps, schema_editor):
    # Get models
    ContentType = apps.get_model("contenttypes.ContentType")
    ReleaseCalendarIndex = apps.get_model("release_calendar", "ReleaseCalendarIndex")
    Page = apps.get_model("wagtailcore.Page")
    Locale = apps.get_model("wagtailcore.Locale")

    # Create content type for the model
    index_content_type, _created = ContentType.objects.get_or_create(
        model="releasecalendarindex", app_label="release_calendar"
    )

    home_page = Page.objects.get(url_path="/home/")
    now = timezone.now()

    # Create a new page
    ReleaseCalendarIndex.objects.create(
        title="Release calendar",
        draft_title="Release calendar",
        live=True,
        first_published_at=now,
        last_published_at=now,
        slug="releases",
        path=f"{home_page.path}00{home_page.numchild + 1:02d}",
        content_type=index_content_type,
        depth=home_page.depth + 1,
        url_path=f"{home_page.url_path}releases/",
        locale=Locale.objects.first(),  # cannot use Locale.get_default(), but since we only have one, this works
    )

    home_page.numchild += 1
    home_page.save()


class Migration(migrations.Migration):
    dependencies = [
        ("home", "0002_create_homepage"),
        ("release_calendar", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_index_page, migrations.RunPython.noop),
    ]
