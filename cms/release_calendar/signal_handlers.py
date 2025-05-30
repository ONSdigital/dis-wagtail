from django.dispatch import receiver
from wagtail.signals import page_published

from cms.release_calendar.models import ReleaseCalendarPage


@receiver(page_published, sender=ReleaseCalendarPage)
def on_release_calendar_page_published(
    sender: ReleaseCalendarPage,  # pylint: disable=unused-argument
    instance: ReleaseCalendarPage,
    **kwargs: dict,
) -> None:
    """Signal handler to update log to frozen when a ReleaseCalendarPage is published."""
    for date_change_log in instance.changes_to_release_date:
        date_change_log.value["frozen"] = True

    instance.save(update_fields=["changes_to_release_date"])
