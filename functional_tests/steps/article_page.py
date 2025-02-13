from behave import given  # pylint: disable=no-name-in-module
from behave.runner import Context

from cms.articles.tests.factories import ArticleSeriesFactory, StatisticalArticlePageFactory


@given("a statistical article page has been published under the existing theme page")
def create_article_page(context: Context):
    context.article_series = ArticleSeriesFactory(parent=context.topic_page)
    context.statistical_article = StatisticalArticlePageFactory(parent=context.article_series)
