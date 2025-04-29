from behave import given, step, then, when  # pylint: disable=no-name-in-module
from behave.runner import Context
from django.urls import reverse
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


@step("the user edits the ancestor topic")
def user_edits_the_ancestor_topic(context: Context):
    edit_url = reverse("wagtailadmin_pages:edit", args=(context.topic_page.id,))
    context.page.goto(f"{context.base_url}{edit_url}")


@step("the user views the topic page")
def user_views_the_topic_page(context: Context):
    context.page.goto(f"{context.base_url}{context.topic_page.url}")


@step("the user clicks to add headline figures to the topic page")
def user_clicks_to_add_headline_figures_to_the_topic_page(context: Context, *, button_index: int = 0):
    page = context.page
    panel = page.locator("#panel-child-content-headline_figures-content")
    panel.get_by_role("button", name="Insert a block").nth(button_index).click()
    page.wait_for_timeout(100)
    panel.get_by_role("button", name="Choose Article Series page and headline figure").click()
    page.wait_for_timeout(100)  # Wait for modal to open


@step("the user adds two headline figures to the topic page")
def user_adds_two_headline_figures_to_the_topic_page(context: Context):
    page = context.page
    user_clicks_to_add_headline_figures_to_the_topic_page(context)
    page.locator(".modal-content").get_by_role("link", name="PSF").nth(0).click()
    user_clicks_to_add_headline_figures_to_the_topic_page(context, button_index=1)
    page.locator(".modal-content").get_by_role("link", name="PSF").nth(1).click()


@step("the user reorders the headline figures on the topic page")
def user_reorders_the_headline_figures_on_the_topic_page(context: Context):
    page = context.page
    panel = page.locator("#panel-child-content-headline_figures-content")
    panel.get_by_role("button", name="Move up").nth(1).click()


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


@then("the published topic page has the added headline figures in the correct order")
def the_published_topic_page_has_the_added_headline_figures_in_the_correct_order(context: Context):
    page = context.page
    headline_block = page.locator(".headline-figures .ons-grid__col")
    expect(headline_block.nth(0).get_by_text("First headline figure")).to_be_visible()
    expect(headline_block.nth(1).get_by_text("Second headline figure")).to_be_visible()


@then("the published topic page has reordered headline figures")
def the_published_topic_page_has_reordered_headline_figures(context: Context):
    page = context.page
    headline_block = page.locator(".headline-figures .ons-grid__col")
    expect(headline_block.nth(0).get_by_text("Second headline figure")).to_be_visible()
    expect(headline_block.nth(1).get_by_text("First headline figure")).to_be_visible()


@then("the headline figures on the topic page link to the statistical page")
def the_headline_figures_on_the_topic_page_link_to_the_statistical_page(context: Context):
    page = context.page
    page.get_by_text("First headline figure").click()
    expect(page.get_by_role("heading", name="The article page")).to_be_visible()
    page.go_back()
    page.get_by_text("Second headline figure").click()
    expect(page.get_by_role("heading", name="The article page")).to_be_visible()
