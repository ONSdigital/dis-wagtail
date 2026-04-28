# pylint: disable=not-callable
from behave import given, then, when
from behave.runner import Context
from playwright.sync_api import expect

from cms.methodology.tests.factories import MethodologyPageFactory
from cms.topics.tests.factories import TopicPageRelatedMethodologyFactory


@given("the topic page has at least 3 child methodologies")
def the_topic_page_has_at_least_3_statistical_articles_in_a_series(
    context: Context,
) -> None:
    """Create 3 methodology pages under the topic page."""
    context.methodologies = MethodologyPageFactory.create_batch(parent__parent=context.topic_page, size=3)


@when('the user adds an external related methodology with title "{title}"')
def user_adds_external_related_methodology(context: Context, title: str) -> None:
    """Add an external related methodology with the given title."""
    # Initialize counter if this is the first article being added in the scenario
    if not hasattr(context, "manual_methodology_index"):
        context.manual_methodology_index = 0

    # Click the main "Add" button
    context.page.locator("#id_related_methodologies-ADD").click()

    # Fill the fields using the dynamic index
    url_field = f"#id_related_methodologies-{context.manual_methodology_index}-external_url"
    content_type_field = f"#id_related_methodologies-{context.manual_methodology_index}-content_type"
    title_field = f"#id_related_methodologies-{context.manual_methodology_index}-title"

    context.page.locator(url_field).fill(f"https://ons.gov.uk/{title.lower().replace(' ', '-')}")
    context.page.locator(content_type_field).select_option(label="Information")
    context.page.locator(title_field).fill(title)

    # Increment the counter
    context.manual_methodology_index += 1


@then('the user can see "{title}" in the related methodologies section')
def user_can_see_title_in_related_methodologies_section(context: Context, title: str) -> None:
    """Assert that the given title is visible in the related methods section."""
    related_articles_section = context.page.locator("section#related-methods")
    expect(related_articles_section.get_by_role("link", name=title)).to_be_visible()


@then('the related methodology "{title}" is the first in the list')
def related_method_is_first_in_list(context: Context, title: str) -> None:
    """Assert that the given title is the first methodology in the list."""
    related_methods_section = context.page.locator("section#related-methods")
    first_method = related_methods_section.locator("li.ons-document-list__item").first
    expect(first_method.get_by_role("link", name=title)).to_be_visible()


@then("the related methods section contains {count:d} methods")
def related_methods_section_contains_count_methods(context: Context, count: int) -> None:
    """Assert that the related articles section contains the expected number of articles."""
    related_methods_section = context.page.locator("section#related-methods")
    methods = related_methods_section.locator("li.ons-document-list__item")
    expect(methods).to_have_count(count)


@then('the related methodology "{title}" is the second in the list')
def related_methodology_is_second_in_list(context: Context, title: str) -> None:
    """Assert that the given title is the second article in the list."""
    related_methods_section = context.page.locator("section#related-methods")
    second_method = related_methods_section.locator("li.ons-document-list__item").nth(1)
    expect(second_method.get_by_role("link", name=title)).to_be_visible()


@then("the related methods section contains only the 3 manually added methods")
def related_methods_section_contains_only_manually_added_articles(
    context: Context,
) -> None:
    """Assert that the related articles section contains only manually added articles (no auto-populated ones)."""
    related_methods_section = context.page.locator("section#related-methods")
    methods = related_methods_section.locator("li.ons-document-list__item")
    expect(methods).to_have_count(3)

    # Check that all three manually added articles are present
    expect(related_methods_section.get_by_role("link", name="Sticky Link 1")).to_be_visible()
    expect(related_methods_section.get_by_role("link", name="Sticky Link 2")).to_be_visible()
    expect(related_methods_section.get_by_role("link", name="Sticky Link 3")).to_be_visible()

    # Check that no auto-populated methods are present
    for method in context.methodologies:
        expect(related_methods_section.get_by_role("link", name=method.title)).not_to_be_visible()


@given("the user has added one external related method to the topic page")
def user_has_added_one_external_related_method(context: Context) -> None:
    """Setup step where user has already added one external related article."""
    TopicPageRelatedMethodologyFactory(
        parent=context.topic_page, page=None, external_url="https://ons.gov.uk/cookies", title="Cookies"
    )


@when("the user removes the first manually added related method")
def user_removes_first_manually_added_related_method(context: Context) -> None:
    """Remove the first manually added related method."""
    # Use the precise selector for the delete button of the first item
    context.page.locator("#id_related_methodologies-0-DELETE-button").click()


@then("the related methods section contains 3 auto-populated methods")
def related_articles_section_contains_auto_populated_methods(context: Context) -> None:
    """Assert that the related methods section contains only auto-populated methods."""
    related_methods_section = context.page.locator("section#related-methods")
    articles = related_methods_section.locator("li.ons-document-list__item")
    expect(articles).to_have_count(3)

    # Check that all three auto-populated methods are present
    for method in context.methodologies:
        expect(related_methods_section.get_by_role("link", name=method.title)).to_be_visible()


@then('the user can see "{title}" in the related methods section')
def user_can_see_title_in_related_methods_section(context: Context, title: str) -> None:
    """Assert that the given title is visible in the related methods section."""
    related_methods_section = context.page.locator("section#related-methods")
    expect(related_methods_section.get_by_role("link", name=title)).to_be_visible()


@when('the user adds an internal related methodology with custom title "{custom_title}"')
def user_adds_internal_related_methodology_with_custom_title(context: Context, custom_title: str) -> None:
    """Add an internal related methodology with a custom title."""
    # Initialize counter if this is the first methodology being added in the scenario
    if not hasattr(context, "manual_methodology_index"):
        context.manual_methodology_index = 0

    # Store the custom title and selected article for later verification
    context.custom_title = custom_title
    context.selected_methodology = context.methodologies[0]  # We'll select the first available methodology

    # Click the main "Add" button
    context.page.locator("#id_related_methodologies-ADD").click()

    # Select an internal page - look for the "Choose a page" button
    context.page.get_by_role("button", name="Choose Methodology page").click()
    context.page.wait_for_timeout(250)  # Wait for the modal to open

    # Click on the methodology in the chooser modal
    modal = context.page.locator("#search-results")
    methodology_link = modal.locator("[data-chooser-modal-choice]").nth(0)
    methodology_link.click()

    # Fill in the custom title
    title_field = f"#id_related_methodologies-{context.manual_methodology_index}-title"
    context.page.locator(title_field).fill(custom_title)

    # Increment the counter
    context.manual_methodology_index += 1


@then("the custom title overrides the methods's original title")
def custom_title_overrides_original_methods_title(context: Context) -> None:
    """Assert that the custom title is displayed instead of the page's original title."""
    related_methods_section = context.page.locator("section#related-methods")

    # Check that the custom title is visible
    expect(related_methods_section.get_by_role("link", name=context.custom_title)).to_be_visible()

    # Check that the original title is not visible in the first position
    first_article = related_methods_section.locator("li.ons-document-list__item").first
    expect(first_article.get_by_role("link", name=context.selected_methodology.title)).not_to_be_visible()
