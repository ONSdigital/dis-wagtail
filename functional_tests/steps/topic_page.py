from behave import given
from behave.runner import Context

from cms.topics.tests.factories import TopicPageFactory


@given("a topic page exists as a child of the existing theme page")
def a_topic_page_already_exists_under_theme_page(context: Context):
    context.topic_page = TopicPageFactory(parent=context.theme_page)
