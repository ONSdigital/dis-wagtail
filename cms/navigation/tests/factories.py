import factory
from wagtail_factories import ListBlockFactory, PageChooserBlockFactory, StreamFieldFactory, StructBlockFactory

from cms.core.tests.factories import LinkBlockFactory
from cms.navigation.blocks import LinksColumn, SectionBlock, ThemeLinkBlock, TopicLinkBlock
from cms.navigation.models import ColumnBlock, FooterMenu, MainMenu, NavigationSettings
from cms.themes.tests.factories import ThemePageFactory
from cms.topics.tests.factories import TopicPageFactory


class ThemePageChooserFactory(PageChooserBlockFactory):
    page = factory.LazyFunction(lambda: ThemePageFactory().id)


class TopicPageChooserFactory(PageChooserBlockFactory):
    page = factory.LazyFunction(lambda: TopicPageFactory().id)


class ThemeLinkBlockFactory(LinkBlockFactory):
    class Meta:
        model = ThemeLinkBlock

    page = factory.SubFactory(ThemePageChooserFactory)


class TopicLinkBlockFactory(LinkBlockFactory):
    class Meta:
        model = TopicLinkBlock

    page = factory.SubFactory(TopicPageChooserFactory)


class HighlightsBlockFactory(LinkBlockFactory):
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


class LinksColumnFactory(StructBlockFactory):
    class Meta:
        model = LinksColumn

    title = factory.Faker("text", max_nb_chars=20)
    links = ListBlockFactory(LinkBlockFactory)


class FooterMenuFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FooterMenu

    columns = StreamFieldFactory(
        {
            "column": LinksColumnFactory,
        }
    )


class NavigationSettingsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = NavigationSettings

    main_menu = factory.SubFactory(MainMenuFactory)
    footer_menu = factory.SubFactory(FooterMenuFactory)
