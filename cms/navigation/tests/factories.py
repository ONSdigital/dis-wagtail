import factory
from wagtail_factories import ListBlockFactory, PageChooserBlockFactory, StreamFieldFactory, StructBlockFactory

from cms.navigation.blocks import SectionBlock, ThemeLinkBlock, TopicLinkBlock
from cms.navigation.models import ColumnBlock, MainMenu, NavigationSettings
from cms.themes.tests.factories import ThemePageFactory
from cms.topics.tests.factories import TopicPageFactory


class ThemePageChooserFactory(PageChooserBlockFactory):
    page = factory.SubFactory(ThemePageFactory)


class TopicPageChooserFactory(PageChooserBlockFactory):
    page = factory.SubFactory(TopicPageFactory)


class ThemeLinkBlockFactory(StructBlockFactory):
    class Meta:
        model = ThemeLinkBlock

    external_url = factory.Faker("url")
    title = factory.Faker("text", max_nb_chars=20)
    page = factory.SubFactory(ThemePageChooserFactory)


class TopicLinkBlockFactory(StructBlockFactory):
    class Meta:
        model = TopicLinkBlock

    external_url = factory.Faker("url")
    title = factory.Faker("text", max_nb_chars=20)
    page = factory.SubFactory(TopicPageChooserFactory)


class HighlightsBlockFactory(StructBlockFactory):
    external_url = factory.Faker("url")
    title = factory.Faker("text", max_nb_chars=20)
    description = factory.Faker("text", max_nb_chars=50)


class SectionBlockFactory(StructBlockFactory):
    class Meta:
        model = SectionBlock

    section_link = factory.SubFactory(ThemeLinkBlockFactory)
    links = ListBlockFactory(TopicLinkBlockFactory)


class ColumnBlockFactory(StructBlockFactory):
    class Meta:
        model = ColumnBlock

    sections = ListBlockFactory(SectionBlockFactory)


class MainMenuFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MainMenu

    highlights = StreamFieldFactory({"highlight": HighlightsBlockFactory})
    columns = StreamFieldFactory(
        {
            "column": ColumnBlockFactory,
        }
    )


class NavigationSettingsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = NavigationSettings

    main_menu = factory.SubFactory(MainMenuFactory)
