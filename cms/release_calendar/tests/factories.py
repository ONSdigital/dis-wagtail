import factory
import wagtail_factories
from django.utils import timezone

from cms.release_calendar.models import ReleaseCalendarIndex, ReleaseCalendarPage


class ReleaseCalendarPageFactory(wagtail_factories.PageFactory):
    """Factory for ReleaseCalendarPage."""

    class Meta:
        model = ReleaseCalendarPage

    parent = factory.LazyFunction(lambda: ReleaseCalendarIndex.objects.first())  # pylint: disable=unnecessary-lambda

    title = factory.Faker("sentence", nb_words=4)
    summary = factory.Faker("text", max_nb_chars=100)
    release_date = factory.LazyFunction(lambda: timezone.now())  # pylint: disable=unnecessary-lambda
