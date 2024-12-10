import wagtail_factories
import factory
from navigation.models import MainMenu, NavigationSettings


class HighlightsBlockFactory(wagtail_factories.StructBlockFactory):
    """Factory for HighlightsBlock."""

    description = factory.Faker("text", max_nb_chars=50)
    link = wagtail_factories.PageChooserBlockFactory()


class SectionBlockFactory(wagtail_factories.StructBlockFactory):
    """Factory for SectionBlock."""

    section_link = wagtail_factories.StructBlockFactory()
    links = wagtail_factories.ListBlockFactory(wagtail_factories.StructBlockFactory())


class ColumnBlockFactory(wagtail_factories.StructBlockFactory):
    """Factory for ColumnBlock."""

    sections = wagtail_factories.ListBlockFactory(SectionBlockFactory)


class MainMenuFactory(factory.django.DjangoModelFactory):
    """Factory for MainMenu."""

    class Meta:
        model = MainMenu

    highlights = wagtail_factories.StreamFieldFactory({"highlight": factory.SubFactory(HighlightsBlockFactory)})
    columns = wagtail_factories.StreamFieldFactory({"column": factory.SubFactory(ColumnBlockFactory)})


class NavigationSettingsFactory(factory.django.DjangoModelFactory):
    """Factory for NavigationSettings."""

    class Meta:
        model = NavigationSettings

    main_menu = factory.SubFactory(MainMenuFactory)
