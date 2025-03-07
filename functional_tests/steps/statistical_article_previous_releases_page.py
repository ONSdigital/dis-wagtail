from behave import given, then, when # pylint: disable=no-name-in-module
from behave.runner import Context

from cms.articles.tests.factories import ArticleSeriesPageFactory, StatisticalArticlePageFactory
from cms.topics.tests.factories import TopicPageFactory

@when('an external user navigates to statistical article in a series previous releases page')
def step_impl(context):
    raise NotImplementedError(u'STEP: When an external user navigates to statistical article in a series previous releases page')


@then('the user should not see pagination')
def step_impl(context):
    raise NotImplementedError(u'STEP: Then the user should not see pagination')

