from django.dispatch import receiver
from wagtail.signals import page_published

from cms.release_calendar.models import ReleaseCalendarPage


@receiver(page_published, sender=ReleaseCalendarPage)
def on_release_calendar_page_published(
    sender: ReleaseCalendarPage,  # pylint: disable=unused-argument
    instance: ReleaseCalendarPage,
    **kwargs: dict,
) -> None:
    """Signal handler for when a ReleaseCalendarPage is published."""
    # Go through the changes_to_release_date streamfield and set frozen to true for all release date changes
    for change in instance.changes_to_release_date:
        change.value["frozen"] = True

    instance.save(update_fields=["changes_to_release_date"])
