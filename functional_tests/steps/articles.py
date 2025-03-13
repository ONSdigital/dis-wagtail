from datetime import timedelta

from behave import given, when  # pylint: disable=no-name-in-module
from behave.runner import Context

from cms.articles.tests.factories import ArticleSeriesPageFactory, StatisticalArticlePageFactory


@given("the user has created a statistical article in a series")
@given("a statistical article page has been published under the topic page")
def create_article_in_a_series(context: Context):
    context.article_series = ArticleSeriesPageFactory(parent=context.topic_page)
    context.article = StatisticalArticlePageFactory(parent=context.article_series)


@given("an article series has been created under the topic page")
def create_article_series(context: Context):
    context.article_series = ArticleSeriesPageFactory(parent=context.topic_page)


@when("the user creates a new statistical article in the series")
def create_a_new_article_in_the_series(context: Context):
    old_article_release_date = context.article.release_date
    context.article = StatisticalArticlePageFactory(
        title="January 2025", release_date=old_article_release_date + timedelta(days=1), parent=context.article_series
    )
