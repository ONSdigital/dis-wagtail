import factory
import wagtail_factories

from cms.release_calendar.models import ReleaseCalendarIndex, ReleaseCalendarPage


class ReleaseCalendarPageFactory(wagtail_factories.PageFactory):
    """Factory for ReleaseCalendarPage."""

    class Meta:
        model = ReleaseCalendarPage

    parent = factory.LazyFunction(lambda: ReleaseCalendarIndex.objects.first())  # pylint: disable=unnecessary-lambda

    title = factory.Faker("text", max_nb_chars=25)
    summary = factory.Faker("text", max_nb_chars=100)
