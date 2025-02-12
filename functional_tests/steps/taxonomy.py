from behave import given, then  # pylint: disable=no-name-in-module
from behave.runner import Context
from playwright.sync_api import expect

from cms.taxonomy.tests.factories import TopicFactory
from cms.themes.tests.factories import ThemePageFactory
from cms.topics.tests.factories import TopicPageFactory


@given("a topic exists")
def a_topic_exists(context: Context) -> None:
    context.existing_topic = TopicFactory(id="123", title="Example Topic", description="Example topic description")


@given("two topics exist")
def two_topics_exists(context: Context) -> None:
    context.existing_topic = TopicFactory(id="0001", title="Example Topic")
    context.existing_topic_2 = TopicFactory(id="0002", title="Example Second Topic")


@given("the topic is already linked to an existing theme page")
def link_existing_topic_to_existing_theme_page(context: Context) -> None:
    context.existing_page = ThemePageFactory(topic=context.existing_topic)


@given("the topic is already linked to an existing topic page")
def link_existing_topic_to_existing_topic_page(context: Context) -> None:
    context.existing_page = TopicPageFactory(topic=context.existing_topic)


@then("they cannot select the topic which is already linked to the other exclusive page")
def user_cannot_select_existing_topic(context: Context) -> None:
    context.page.get_by_role("tab", name="Taxonomy").click()
    context.page.get_by_role("button", name="Choose a topic").click()
    expect(context.page.get_by_role("link", name=context.existing_topic.title)).not_to_be_visible()


@then("the CMS user can link the page to the existing topic in the taxonomy editor tab")
def user_can_link_existing_topic(context: Context) -> None:
    context.page.get_by_role("tab", name="Taxonomy").click()
    context.page.get_by_role("button", name="Choose a topic").click()
    context.page.get_by_role("link", name=context.existing_topic.title).click()


@then("the user can link the page to both topics in the taxonomy editor tab")
def user_can_link_both_existing_topics(context: Context) -> None:
    context.page.get_by_role("tab", name="Taxonomy").click()
    context.page.get_by_role("button", name="Add topics").click()
    context.page.get_by_role("button", name="Choose a topic").click()
    context.page.get_by_role("link", name=context.existing_topic.title).click()
    context.page.get_by_role("button", name="Add topics").click()
    context.page.get_by_role("button", name="Choose a topic").click()
    context.page.get_by_role("link", name=context.existing_topic_2.title).click()
