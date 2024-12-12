import factory
from wagtail_factories import StreamFieldFactory, StructBlockFactory, ListBlockFactory
from cms.navigation.models import MainMenu, NavigationSettings


class ThemeLinkBlockFactory(StructBlockFactory):
    url = factory.Faker("url")
    title = factory.Faker("sentence", nb_words=3)
    page = factory.SubFactory(
        "wagtail_factories.PageFactory",
        page_type="themes.ThemePage",
    )


class TopicLinkBlockFactory(StructBlockFactory):
    url = factory.Faker("url")
    title = factory.Faker("sentence", nb_words=3)
    page = factory.SubFactory(
        "wagtail_factories.PageFactory",
        page_type="topic.TopicPage",
    )


class HighlightsBlockFactory(StructBlockFactory):
    url = factory.Faker("url")
    title = factory.Faker("sentence", nb_words=3)
    description = factory.Faker("sentence", nb_words=10)


class SectionBlockFactory(StructBlockFactory):
    section_link = factory.SubFactory(ThemeLinkBlockFactory)
    links = ListBlockFactory(TopicLinkBlockFactory, size=3)


class ColumnBlockFactory(StructBlockFactory):
    sections = ListBlockFactory(SectionBlockFactory, size=3)


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
