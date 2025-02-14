from behave import given  # pylint: disable=no-name-in-module
from behave.runner import Context

from cms.articles.tests.factories import ArticleSeriesPageFactory, StatisticalArticlePageFactory


@given("the user has created a statistical article in a series")
@given("a statistical article page has been published under the topic page")
def create_article_in_a_series(context: Context):
    context.article_series = ArticleSeriesPageFactory(parent=context.topic_page)
    context.article = StatisticalArticlePageFactory(title="January 2025", parent=context.article_series)
