# pylint: disable=not-callable
from behave import given, then, when
from behave.runner import Context
from django.urls import reverse
from playwright.sync_api import expect

from cms.articles.tests.factories import (
    ArticleSeriesPageFactory,
    StatisticalArticlePageFactory,
)
from functional_tests.step_helpers.users import create_user


@given("a superuser logs into the admin site")
def superuser_logs_into_admin_site(context: Context) -> None:
    """Create a superuser and log them into the admin site."""
    context.user_data = create_user(user_type="superuser")
    context.page.goto(f"{context.base_url}/admin/login/")
    context.page.get_by_placeholder("Enter your username").fill(context.user_data["username"])
    context.page.get_by_placeholder("Enter password").fill(context.user_data["password"])
    context.page.get_by_role("button", name="Sign in").click()


@given("the topic page has at least 3 series with a statistical article")
def the_topic_page_has_at_least_3_statistical_articles_in_a_series(
    context: Context,
) -> None:
    """Create 3 article series with statistical articles."""
    article_series_page_alpha = ArticleSeriesPageFactory(parent=context.topic_page, title="Alpha Series")
    article_series_page_beta = ArticleSeriesPageFactory(parent=context.topic_page, title="Beta Series")
    article_series_page_gamma = ArticleSeriesPageFactory(parent=context.topic_page, title="Gamma Series")

    context.statistical_articles = [
        StatisticalArticlePageFactory(parent=article_series_page_alpha),
        StatisticalArticlePageFactory(parent=article_series_page_beta),
        StatisticalArticlePageFactory(parent=article_series_page_gamma),
    ]


@given("the user has added one external related article to the topic page")
def user_has_added_one_external_related_article(context: Context) -> None:
    """Setup step where user has already added one external related article."""
    # Navigate to edit page
    edit_url = reverse("wagtailadmin_pages:edit", args=(context.topic_page.id,))
    context.page.goto(f"{context.base_url}{edit_url}")

    # Initialize the counter
    context.manual_article_index = 0

    # Add one external article
    context.page.locator("#id_related_articles-ADD").click()
    context.page.locator(f"#id_related_articles-{context.manual_article_index}-external_url").fill(
        "https://example.com/test-article"
    )
    context.page.locator(f"#id_related_articles-{context.manual_article_index}-title").fill("Test External Article")
    context.manual_article_index += 1

    # Publish the page
    context.page.get_by_role("button", name="More actions").click()
    context.page.get_by_role("button", name="Publish").click()


@when('the user adds an external related article with title "{title}" and a short description')
def user_adds_external_related_article(context: Context, title: str) -> None:
    """Add an external related article with the given title."""
    # Initialize counter if this is the first article being added in the scenario
    if not hasattr(context, "manual_article_index"):
        context.manual_article_index = 0

    # Click the main "Add" button
    context.page.locator("#id_related_articles-ADD").click()

    # Fill the fields using the dynamic index
    url_field = f"#id_related_articles-{context.manual_article_index}-external_url"
    title_field = f"#id_related_articles-{context.manual_article_index}-title"

    context.page.locator(url_field).fill(f"https://example.com/{title.lower().replace(' ', '-')}")
    context.page.locator(title_field).fill(title)

    # Increment the counter
    context.manual_article_index += 1


@when("the user removes the first manually added related article")
def user_removes_first_manually_added_related_article(context: Context) -> None:
    """Remove the first manually added related article."""
    # Use the precise selector for the delete button of the first item
    context.page.locator("#id_related_articles-0-DELETE-button").click()


@then('the user can see "{title}" in the related articles section')
def user_can_see_title_in_related_articles_section(context: Context, title: str) -> None:
    """Assert that the given title is visible in the related articles section."""
    related_articles_section = context.page.locator("section#related-articles")
    expect(related_articles_section.get_by_role("link", name=title)).to_be_visible()


@then('the related article "{title}" appears at the top of the list')
def related_article_appears_at_top_of_list(context: Context, title: str) -> None:
    """Assert that the given title appears first in the related articles list."""
    related_articles_section = context.page.locator("section#related-articles")
    first_article = related_articles_section.locator("li.ons-document-list__item").first
    expect(first_article.get_by_role("link", name=title)).to_be_visible()


@then("the related articles section contains {count:d} articles")
def related_articles_section_contains_count_articles(context: Context, count: int) -> None:
    """Assert that the related articles section contains the expected number of articles."""
    related_articles_section = context.page.locator("section#related-articles")
    articles = related_articles_section.locator("li.ons-document-list__item")
    expect(articles).to_have_count(count)


@then('the related article "{title}" is the first in the list')
def related_article_is_first_in_list(context: Context, title: str) -> None:
    """Assert that the given title is the first article in the list."""
    related_articles_section = context.page.locator("section#related-articles")
    first_article = related_articles_section.locator("li.ons-document-list__item").first
    expect(first_article.get_by_role("link", name=title)).to_be_visible()


@then('the related article "{title}" is the second in the list')
def related_article_is_second_in_list(context: Context, title: str) -> None:
    """Assert that the given title is the second article in the list."""
    related_articles_section = context.page.locator("section#related-articles")
    second_article = related_articles_section.locator("li.ons-document-list__item").nth(1)
    expect(second_article.get_by_role("link", name=title)).to_be_visible()


@then("the related articles section contains only the 3 manually added articles")
def related_articles_section_contains_only_manually_added_articles(
    context: Context,
) -> None:
    """Assert that the related articles section contains only manually added articles (no auto-populated ones)."""
    related_articles_section = context.page.locator("section#related-articles")
    articles = related_articles_section.locator("li.ons-document-list__item")
    expect(articles).to_have_count(3)

    # Check that all three manually added articles are present
    expect(related_articles_section.get_by_role("link", name="Sticky Link 1")).to_be_visible()
    expect(related_articles_section.get_by_role("link", name="Sticky Link 2")).to_be_visible()
    expect(related_articles_section.get_by_role("link", name="Sticky Link 3")).to_be_visible()

    # Check that no auto-populated articles are present
    for article in context.statistical_articles:
        expect(related_articles_section.get_by_role("link", name=article.display_title)).not_to_be_visible()


@then("the related articles section contains 3 auto-populated articles")
def related_articles_section_contains_auto_populated_articles(context: Context) -> None:
    """Assert that the related articles section contains only auto-populated articles."""
    related_articles_section = context.page.locator("section#related-articles")
    articles = related_articles_section.locator("li.ons-document-list__item")
    expect(articles).to_have_count(3)

    # Check that all three auto-populated articles are present
    for article in context.statistical_articles:
        expect(related_articles_section.get_by_role("link", name=article.display_title)).to_be_visible()


@when('the user adds an internal related article with custom title "{custom_title}"')
def user_adds_internal_related_article_with_custom_title(context: Context, custom_title: str) -> None:
    """Add an internal related article with a custom title."""
    # Initialize counter if this is the first article being added in the scenario
    if not hasattr(context, "manual_article_index"):
        context.manual_article_index = 0

    # Store the custom title and selected article for later verification
    context.custom_title = custom_title
    context.selected_article = context.statistical_articles[0]  # We'll select the first available article

    # Click the main "Add" button
    context.page.locator("#id_related_articles-ADD").click()

    # Select an internal page - look for the "Choose a page" button
    context.page.get_by_role("button", name="Choose Article page").click()
    context.page.wait_for_timeout(250)  # Wait for the modal to open

    # Click on the article in the chooser modal
    modal = context.page.locator("#search-results")
    article_link = modal.locator("[data-chooser-modal-choice]").nth(0)
    article_link.click()

    # Fill in the custom title
    title_field = f"#id_related_articles-{context.manual_article_index}-title"
    context.page.locator(title_field).fill(custom_title)

    # Increment the counter
    context.manual_article_index += 1


@then("the custom title overrides the page's original title")
def custom_title_overrides_original_title(context: Context) -> None:
    """Assert that the custom title is displayed instead of the page's original title."""
    related_articles_section = context.page.locator("section#related-articles")

    # Check that the custom title is visible
    expect(related_articles_section.get_by_role("link", name=context.custom_title)).to_be_visible()

    # Check that the original title is not visible in the first position
    first_article = related_articles_section.locator("li.ons-document-list__item").first
    expect(first_article.get_by_role("link", name=context.selected_article.display_title)).not_to_be_visible()
