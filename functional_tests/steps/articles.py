from behave import given, when  # pylint: disable=no-name-in-module
from behave.runner import Context

from cms.articles.tests.factories import ArticleSeriesPageFactory, StatisticalArticlePageFactory


@given("the user creates a new article series")
@given("the user has created a statistical article in a series")
def create_article_series(context: Context):
    context.article_series = ArticleSeriesPageFactory()


@when("the user creates a new statistical article in the series")
def create_article_in_series(context: Context):
    context.article = StatisticalArticlePageFactory(title="January 2025", parent=context.article_series)
