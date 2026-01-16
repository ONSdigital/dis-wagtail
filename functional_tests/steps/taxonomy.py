# pylint: disable=not-callable
from behave import given, step, then
from behave.runner import Context
from playwright.sync_api import expect

from cms.taxonomy.tests.factories import TopicFactory
from cms.themes.tests.factories import ThemePageFactory
from cms.topics.tests.factories import TopicPageFactory


@given("a topic exists")
def a_topic_exists(context: Context) -> None:
    context.existing_topic = TopicFactory(id="0001", title="Example Topic", description="Example topic description")


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


@then("the topic which is linked already exclusively linked does not show in the page taxonomy topic chooser")
def user_cannot_select_existing_topic(context: Context) -> None:
    context.page.get_by_role("tab", name="Taxonomy").click()
    context.page.get_by_role("button", name="Choose a topic").click()
    expect(context.page.get_by_role("link", name=context.existing_topic.title)).not_to_be_visible()


@step("the user goes to the Taxonomy tab")
def user_goes_to_taxonomy_tab(context: Context) -> None:
    context.page.get_by_role("tab", name="Taxonomy").click()


@then("the user can link the page to the existing topic in the taxonomy editor tab")
def user_can_link_existing_topic(context: Context) -> None:
    context.page.get_by_role("tab", name="Taxonomy").click()
    context.page.get_by_role("button", name="Choose a topic").click()
    context.page.get_by_role("link", name=context.existing_topic.title).click()


@then("the user can tag the page with both topics in the taxonomy editor tab")
def user_can_link_both_existing_topics(context: Context) -> None:
    context.page.get_by_role("tab", name="Taxonomy").click()
    context.page.get_by_role("button", name="Add topics").click()
    context.page.get_by_text(context.existing_topic.title).click()
    context.page.get_by_text(context.existing_topic_2.title).click()
    context.page.get_by_role("button", name="Confirm selection").click()


@then("the user is informed that the selected topic is copied from the English version")
def user_is_informed_topic_copied(context: Context) -> None:
    expect(
        context.page.get_by_text("This page will use the topic selected in the English version of the page")
    ).to_be_visible()
