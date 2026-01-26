# pylint: disable=not-callable
from behave import given, step, then, when
from behave.runner import Context
from django.conf import settings
from django.urls import reverse
from playwright.sync_api import expect

from cms.articles.tests.factories import (
    ArticleSeriesPageFactory,
    ArticlesIndexPageFactory,
    StatisticalArticlePageFactory,
)
from cms.methodology.tests.factories import MethodologyIndexPageFactory, MethodologyPageFactory
from cms.topics.tests.factories import TopicPageFactory
from functional_tests.step_helpers.topic_page_utils import TopicContentBuilder
from functional_tests.step_helpers.utils import get_page_from_context


@given("a topic page exists under the homepage")
def the_user_creates_topic_page(context: Context) -> None:
    context.topic_page = TopicPageFactory(title="Public Sector Finance")


@given("the topic page has a statistical article in a series")
def the_topic_page_has_a_statistical_article_in_a_series(context: Context) -> None:
    context.article_index_page = ArticlesIndexPageFactory(parent=context.topic_page)
    context.article_series_page = ArticleSeriesPageFactory(parent=context.article_index_page, title="PSF")
    context.first_statistical_article_page = StatisticalArticlePageFactory(parent=context.article_series_page)


@given("the topic page has a child methodology page")
def the_topic_page_has_a_child_methodology_page(context: Context) -> None:
    context.methodology_index_page = MethodologyIndexPageFactory(parent=context.topic_page)
    context.methodology_page = MethodologyPageFactory(parent=context.methodology_index_page)


@given("the user has featured the series")
def the_user_has_featured_the_series(context: Context) -> None:
    context.topic_page.featured_series = context.article_series_page
    context.topic_page.save_revision().publish()


@when("the user visits the topic page")
def visit_topic_page(context: Context) -> None:
    context.page.goto(f"{context.base_url}{context.topic_page.url}")


@when("the user selects the article series")
def the_user_select_article_series(context: Context) -> None:
    context.page.get_by_role("link", name=context.article_series_page.title, exact=True).click()


@step("the user edits the ancestor topic")
def user_edits_the_ancestor_topic(context: Context) -> None:
    edit_url = reverse("wagtailadmin_pages:edit", args=(context.topic_page.id,))
    context.page.goto(f"{context.base_url}{edit_url}")


@step("the user views the topic page")
def user_views_the_topic_page(context: Context) -> None:
    context.page.goto(f"{context.base_url}{context.topic_page.url}")


@step("the user clicks to add headline figures to the topic page")
def user_clicks_to_add_headline_figures_to_the_topic_page(context: Context, *, button_index: int = 0) -> None:
    page = context.page
    panel = page.locator("#panel-child-content-headline_figures-content")
    panel.get_by_role("button", name="Insert a block").nth(button_index).click()
    page.wait_for_timeout(100)
    panel.get_by_role("button", name="Choose Article Series page and headline figure").click()
    page.wait_for_timeout(100)  # Wait for modal to open


@step("the user adds two headline figures to the topic page")
def user_adds_two_headline_figures_to_the_topic_page(context: Context) -> None:
    page = context.page
    user_clicks_to_add_headline_figures_to_the_topic_page(context)
    page.locator(".modal-content").get_by_role("link", name="PSF").nth(0).click()
    user_clicks_to_add_headline_figures_to_the_topic_page(context, button_index=1)
    page.locator(".modal-content").get_by_role("link", name="PSF").nth(1).click()


@step("the user reorders the headline figures on the topic page")
def user_reorders_the_headline_figures_on_the_topic_page(context: Context) -> None:
    page = context.page
    panel = page.locator("#panel-child-content-headline_figures-content")
    panel.get_by_role("button", name="Move up").nth(1).click()


@then("the topic page with the example content is displayed")
def the_topic_page_with_example_content(context: Context) -> None:
    expect(context.page.get_by_role("heading", name=context.topic_page.title)).to_be_visible()


@then("the user can see the topic page featured article")
def user_sees_featured_article(context: Context) -> None:
    expect(context.page.get_by_role("heading", name="Featured")).to_be_visible()
    featured_section = context.page.locator("#featured")
    expect(featured_section.get_by_text(context.first_statistical_article_page.display_title)).to_be_visible()
    expect(featured_section.get_by_text(context.first_statistical_article_page.main_points_summary)).to_be_visible()


@then("the user can see the newly created article in featured spot")
def user_sees_newly_featured_article(context: Context) -> None:
    expect(context.page.get_by_role("heading", name="Featured")).to_be_visible()
    expect(
        context.page.locator("#featured").get_by_text(context.new_statistical_article_page.display_title)
    ).to_be_visible()
    expect(
        context.page.locator("#featured").get_by_text(context.new_statistical_article_page.main_points_summary)
    ).to_be_visible()


@then("the published topic page has the added headline figures in the correct order")
def the_published_topic_page_has_the_added_headline_figures_in_the_correct_order(
    context: Context,
) -> None:
    page = context.page
    headline_block = page.locator("#headline-figures .ons-grid__col")
    expect(headline_block.nth(0).get_by_text("First headline figure")).to_be_visible()
    expect(headline_block.nth(1).get_by_text("Second headline figure")).to_be_visible()


@then("the published topic page has reordered headline figures")
def the_published_topic_page_has_reordered_headline_figures(context: Context) -> None:
    page = context.page
    headline_block = page.locator("#headline-figures .ons-grid__col")
    expect(headline_block.nth(0).get_by_text("Second headline figure")).to_be_visible()
    expect(headline_block.nth(1).get_by_text("First headline figure")).to_be_visible()


@then("the headline figures on the topic page link to the statistical page")
def the_headline_figures_on_the_topic_page_link_to_the_statistical_page(
    context: Context,
) -> None:
    the_page = get_page_from_context(context, "statistical article")
    context.page.get_by_text("First headline figure").click()
    expect(context.page.get_by_role("heading", name=the_page.display_title)).to_be_visible()
    context.page.go_back()
    context.page.get_by_text("Second headline figure").click()
    expect(context.page.get_by_role("heading", name=the_page.display_title)).to_be_visible()


@when("the user adds a time series page link")
def the_user_adds_a_time_series_page_link(context: Context) -> None:
    page = context.page
    page.locator("#panel-child-content-time_series-content").get_by_role("button", name="Insert a block").click()
    page.get_by_role("region", name="Time series page link").get_by_label("Title*").fill("Page title")
    page.get_by_role("textbox", name="Url*").fill(settings.ONS_WEBSITE_BASE_URL + "/time-series/")
    page.get_by_role("textbox", name="Description*").fill("Page summary for time series example")


@then("the time series section is displayed on the page")
def the_time_series_page_link_is_displayed_on_the_page(context: Context) -> None:
    page = context.page

    expect(
        page.locator("#time-series").get_by_role("heading", name="Time Series", exact=True)
    ).to_be_visible()  # Section heading
    expect(page.locator("#time-series").get_by_role("link", name="Page title")).to_be_visible()
    expect(page.locator("#time-series").get_by_text("Time series", exact=True)).to_be_visible()  # Content type label
    expect(page.locator("#time-series").get_by_text("Summary")).to_be_visible()


@then("the time series item appears in the table of contents")
def the_time_series_item_appears_in_the_table_of_contents(context: Context) -> None:
    expect(context.page.get_by_role("heading", name="Time Series")).to_be_visible()


@then("the user sees the '{link_text}' link")
def user_can_see_link(context: Context, link_text: str) -> None:
    expect(context.page.get_by_role("link", name=link_text)).to_be_visible()


@given("the following topic pages exist:")
def create_topic_pages_from_table(context: Context) -> None:
    """Create multiple topic pages from a table."""
    context.topic_pages = {}  # Store all topic pages by title

    # Initialise builder if not exists
    if not hasattr(context, "topic_page_builder"):
        context.topic_page_builder = TopicContentBuilder()

    for row in context.table:
        title = row["title"]
        topic_name = row["topic"]

        # Create or reuse the topic
        topic = context.topic_page_builder.get_or_create_topic(topic_name)

        # Create the topic page
        topic_page = TopicPageFactory(title=title, topic=topic)

        # Store it in context for later reference
        context.topic_pages[title] = topic_page


@given('"{topic_page_title}" has the following "{item_type}":')
def create_items_for_topic_page(context: Context, topic_page_title: str, item_type: str) -> None:
    """Create articles or methodologies under a specific topic page."""
    topic_page = context.topic_pages[topic_page_title]

    if not hasattr(context, "topic_page_builder"):
        context.topic_page_builder = TopicContentBuilder()

    items_data = [row.as_dict() for row in context.table]

    # Map item_type to builder method and context attribute
    builder_methods = {
        "articles": context.topic_page_builder.create_articles_for_topic_page,
        "methodologies": context.topic_page_builder.create_methodologies_for_topic_page,
    }

    if item_type not in builder_methods:
        raise ValueError(f"Unsupported item_type: {item_type}")

    builder_methods[item_type](topic_page, items_data)


@when('the user visits "{topic_page_title}"')
def user_visits_topic_page(context: Context, topic_page_title: str) -> None:
    topic_page = context.topic_pages[topic_page_title]
    context.page.goto(f"{context.base_url}{topic_page.url}")


@when('the user edits "{topic_page_title}"')
def user_edits_topic_page(context: Context, topic_page_title: str) -> None:
    topic_page = context.topic_pages[topic_page_title]
    edit_url = reverse("wagtailadmin_pages:edit", args=[topic_page.id])
    context.page.goto(f"{context.base_url}{edit_url}")


@when('the user manually adds "{item_title}" in the highlighted "{item_type}" section')
def user_manually_adds_item(context: Context, item_title: str, item_type: str) -> None:
    button_map = {
        "articles": ("Add topic page related article", "Choose Article page"),
        "methodologies": ("Add topic page related methodology", "Choose Methodology page"),
    }

    if item_type not in button_map:
        raise ValueError(f"Unsupported item_type: {item_type}")

    add_button, choose_button = button_map[item_type]
    context.page.get_by_role("button", name=add_button).click()
    context.page.get_by_role("button", name=choose_button).click()
    context.page.get_by_role("link", name=item_title).click()


@then('the highlighted "{section_type}" section is visible')
def highlighted_section_visible(context: Context, section_type: str) -> None:
    """Check if the highlighted articles or methodologies section is visible."""
    section_map = {
        "articles": ("#related-articles", "Related articles"),
        "methodologies": ("#related-methods", "Methods and quality information"),
    }

    if section_type not in section_map:
        raise ValueError(f"Unsupported section_type: {section_type}")

    selector, expected_text = section_map[section_type]
    expect(context.page.locator(selector)).to_contain_text(expected_text)


@then('the highlighted "{item_type}" are displayed in this order:')
def check_highlighted_items_order(context: Context, item_type: str) -> None:
    """Check the order of highlighted articles or methodologies matches the table."""
    expected_titles = [row[0] for row in context.table]
    document_list = context.page.locator(".ons-document-list").first
    list_items = document_list.locator(".ons-document-list__item").all()

    actual_titles = []
    for item in list_items:
        title_link = item.locator(".ons-document-list__item-title a").first
        title = title_link.text_content().strip()
        actual_titles.append(title)

    assert len(actual_titles) == len(expected_titles), (
        f"Expected {len(expected_titles)} {item_type}, but found {len(actual_titles)}"
    )

    assert actual_titles == expected_titles, f"Expected {item_type} in order {expected_titles}, but got {actual_titles}"

    for title in expected_titles:
        link = document_list.locator(".ons-document-list__item-title a").filter(has_text=title).first
        expect(link).to_be_visible()
