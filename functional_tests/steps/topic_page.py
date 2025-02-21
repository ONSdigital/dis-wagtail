from behave import given, then, when  # pylint: disable=no-name-in-module
from behave.runner import Context
from playwright.sync_api import expect

from cms.articles.tests.factories import ArticleSeriesPageFactory, StatisticalArticlePageFactory
from cms.themes.tests.factories import ThemePageFactory
from cms.topics.tests.factories import TopicPageFactory


@given("a topic page exists under a theme page")
def the_user_creates_theme_and_topic_pages(context: Context):
    context.theme_page = ThemePageFactory()
    context.topic_page = TopicPageFactory(parent=context.theme_page, title="Public Sector Finance")


@given("the topic page has a statistical article in a series")
def the_topic_page_has_a_statistical_article_in_a_series(context: Context):
    context.article_series = ArticleSeriesPageFactory(title="PSF")
    context.first_article = StatisticalArticlePageFactory(parent=context.article_series)


@given("the user has featured the series")
def the_user_has_featured_the_series(context: Context):
    context.topic_page.featured_series = context.article_series
    context.topic_page.save_revision().publish()


@when("the user visits the topic page")
def visit_topic_page(context: Context):
    context.page.goto(f"{context.base_url}{context.topic_page.url}")


@when("the user selects the article series")
def the_user_select_article_series(context: Context):
    context.page.get_by_role("link", name=context.article_series.title, exact=True).click()


@then("the topic page with the example content is displayed")
def the_topic_page_with_example_content(context: Context):
    expect(context.page.get_by_role("heading", name=context.topic_page.title)).to_be_visible()


@then("the user can see the topic page featured article")
def user_sees_featured_article(context: Context):
    expect(context.page.get_by_role("heading", name="Featured")).to_be_visible()
    expect(context.page.get_by_text(context.first_article.display_title)).to_be_visible()
    expect(context.page.get_by_text(context.first_article.main_points_summary)).to_be_visible()


@then("the user can see the newly created article in featured spot")
def user_sees_newly_featured_article(context: Context):
    expect(context.page.get_by_role("heading", name="Featured")).to_be_visible()
    expect(context.page.locator("#featured").get_by_text(context.article.display_title)).to_be_visible()
    expect(context.page.locator("#featured").get_by_text(context.article.main_points_summary)).to_be_visible()
