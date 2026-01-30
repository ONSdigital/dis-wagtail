# pylint: disable=not-callable
from behave import given, then, when
from behave.runner import Context
from playwright.sync_api import expect

from cms.articles.tests.factories import (
    ArticleSeriesPageFactory,
    StatisticalArticlePageFactory,
)


@given("a statistical article page with sections exists")
def a_statistical_article_page_with_sections_exists(context: Context) -> None:
    """Create a statistical article page with multiple sections for TOC testing."""
    context.article_series_page = ArticleSeriesPageFactory(title="Test Series")
    content = [
        {
            "type": "section",
            "value": {
                "title": "Main findings",
                "content": [
                    {
                        "type": "rich_text",
                        "value": "<p>First section content with enough text to make it scrollable.</p>" * 20,
                    }
                ],
            },
        },
        {
            "type": "section",
            "value": {
                "title": "Data sources",
                "content": [
                    {
                        "type": "rich_text",
                        "value": "<p>Second section content.</p>" * 20,
                    }
                ],
            },
        },
    ]
    context.statistical_article_page = StatisticalArticlePageFactory(
        parent=context.article_series_page,
        title="Article with sections",
        content=content,
        show_cite_this_page=True,
    )
    context.statistical_article_page.save()


@when("the user visits the statistical article page")
def user_visits_the_statistical_article_page(context: Context) -> None:
    """Navigate to the statistical article page."""
    context.page.goto(context.statistical_article_page.full_url)


@then("they should see the table of contents")
def user_sees_table_of_contents(context: Context) -> None:
    """Verify the table of contents is visible with expected items."""
    toc = context.page.locator("nav.ons-table-of-contents")
    expect(toc).to_be_visible()
    expect(toc.get_by_role("heading", name="Contents")).to_be_visible()
    expect(toc.get_by_role("link", name="Main findings", exact=True)).to_be_visible()
    expect(toc.get_by_role("link", name="Data sources", exact=True)).to_be_visible()
    expect(toc.get_by_role("link", name="Cite this article", exact=True)).to_be_visible()


@then("they should see the first item highlighted in the table of contents")
def user_sees_first_item_highlighted(context: Context) -> None:
    """Verify the first TOC item has the active class."""
    toc = context.page.locator("nav.ons-table-of-contents")
    first_link = toc.get_by_role("link", name="Main findings", exact=True)
    expect(first_link).to_have_class("ons-list__link ons-table-of-contents__link-active")


@when("they scroll to the second section")
def user_scrolls_to_second_section(context: Context) -> None:
    """Scroll to the second section heading."""
    second_section = context.page.locator("#data-sources")
    second_section.scroll_into_view_if_needed()
    # Wait for the intersection observer to update the active state
    context.page.wait_for_timeout(500)


@when("they click on the second item in the table of contents")
def user_clicks_second_toc_item(context: Context) -> None:
    """Click on the second item in the table of contents."""
    toc = context.page.locator("nav.ons-table-of-contents")
    toc.get_by_role("link", name="Data sources", exact=True).click()
    # Wait for the page to scroll and intersection observer to update
    context.page.wait_for_timeout(500)


@when("they scroll back to the top of the page")
def user_scrolls_to_top(context: Context) -> None:
    """Scroll back to the top of the page."""
    context.page.locator("#main-findings").scroll_into_view_if_needed()
    # Wait for the intersection observer to update the active state
    context.page.wait_for_timeout(500)


@then("they should see the second item highlighted in the table of contents")
def user_sees_second_item_highlighted(context: Context) -> None:
    """Verify the second TOC item has the active class after scrolling."""
    toc = context.page.locator("nav.ons-table-of-contents")
    second_link = toc.get_by_role("link", name="Data sources", exact=True)
    expect(second_link).to_have_class("ons-list__link ons-table-of-contents__link-active")
