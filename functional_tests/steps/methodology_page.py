# pylint: disable=not-callable
from behave import step, then, when
from behave.runner import Context
from playwright.sync_api import expect

from cms.methodology.tests.factories import MethodologyIndexPageFactory


@step("the user creates a methodology page as a child of the existing topic page")
def user_creates_methodology_page(context: Context) -> None:
    methodology_index = MethodologyIndexPageFactory(parent=context.topic_page)
    context.page.get_by_role("button", name="Pages").click()
    context.page.get_by_role("link", name="View child pages of 'Home'").first.click()
    context.page.get_by_role("link", name=f"View child pages of '{context.topic_page.title}'").click()
    context.page.get_by_role("link", name=methodology_index.title, exact=True).click()
    context.page.get_by_role("link", name="Add child page", exact=True).click()


@step("the user populates the methodology page")
def user_populates_the_methodology_page(context: Context) -> None:
    context.page.get_by_placeholder("Page title*").fill("Methodology page")
    context.page.get_by_role("region", name="Summary*").get_by_role("textbox").fill("Page summary")

    context.page.get_by_label("Publication date*").fill("1950-01-01")

    context.page.get_by_title("Insert a block").click()

    context.page.get_by_label("Section heading*").fill("Heading")
    context.page.locator("#panel-child-content-content-content").get_by_role("region").get_by_role(
        "button", name="Insert a block"
    ).click()
    context.page.get_by_text("Rich text").click()
    context.page.get_by_role("region", name="Rich text *").get_by_role("textbox").fill("Content")

    # Scroll to the bottom of the page to ensure that the "Save as draft" button is not overlapped
    context.page.get_by_text("Related publications", exact=True).nth(1).scroll_into_view_if_needed()


@when("adds Definitions to the page content")
def user_adds_definitions(context: Context) -> None:
    context.page.get_by_role("button", name="Insert a block").nth(2).click()
    context.page.wait_for_timeout(500)  # ensure that the Definitions option is ready
    context.page.get_by_role("option", name="Definitions").click()
    context.page.get_by_role("button", name="Choose definition").click()
    context.page.get_by_role("link", name="Term", exact=True).click()


@then("the published methodology page is displayed with the populated data")
def the_methodology_page_is_displayed_with_the_populated_data(context: Context) -> None:
    expect(context.page.get_by_role("heading", name="Methodology page")).to_be_visible()
    expect(context.page.get_by_text("Page summary")).to_be_visible()
    expect(context.page.get_by_text("Published: 1 January 1950")).to_be_visible()
    expect(context.page.get_by_role("heading", name="Cite this methodology")).to_be_visible()

    expect(context.page.get_by_role("heading", name="Heading")).to_be_visible()
    expect(context.page.get_by_role("heading", name="Content")).to_be_visible()


@when("the user selects the article page in the Related publications block")
def the_user_selects_statistical_articles_as_related_publications(
    context: Context,
) -> None:
    context.page.get_by_role("button", name="Add related publications").click()
    context.page.get_by_role("button", name="Choose a page (Statistical").click()
    context.page.get_by_role(
        "cell",
        name=f"{context.article_series_page.title}: {context.statistical_article_page.title}",
    ).click()


@then("the article is displayed correctly under the Related publication section")
def related_publications_are_displayed_correctly(context: Context) -> None:
    expect(context.page.get_by_role("heading", name="Related publications")).to_be_visible()
    expect(context.page.locator("li").filter(has_text=f"{context.topic_page.title}")).to_be_visible()


@when("the user selects the Contact Details")
def user_selects_the_contact_details(context: Context) -> None:
    context.page.get_by_role("button", name="Choose contact details").click()
    context.page.get_by_role("link", name=context.contact_details_snippet.name).click()


@then("the Contact Details are visible on the page")
def contact_details_are_visible_on_the_page(context: Context) -> None:
    # in the header
    expect(context.page.get_by_text(f"Contact: {context.contact_details_snippet.name}")).to_be_visible()
    # in the section
    expect(context.page.get_by_role("heading", name="Contact details")).to_be_visible()
    contact_link = context.page.get_by_role("link", name=context.contact_details_snippet.name)
    expect(contact_link).to_be_visible()
    expect(contact_link).to_have_attribute("href", f"mailto:{context.contact_details_snippet.email}")


@when("the Last revised date is set to be before the Publication date")
def set_last_revised_date_before_publication_date(context: Context) -> None:
    context.page.get_by_label("Publication date*").fill("1950-01-02")
    context.page.get_by_label("Last revised date").fill("1950-01-01")


@then("a validation error for the Last revised date is displayed")
def validation_error_displayed_when_incorrect_date_selected(context: Context) -> None:
    expect(context.page.get_by_text("The last revised date must be after the published date.")).to_be_visible()


@then("the methodology page mandatory fields raise validation errors")
def mandatory_fields_raise_validation_error_when_not_set(context: Context) -> None:
    expect(context.page.get_by_text("The page could not be created due to validation errors")).to_be_visible()

    expect(
        context.page.locator("#panel-child-content-child-title-errors .error-message").get_by_text(
            "This field is required"
        )
    ).to_be_visible()

    expect(
        context.page.locator("#panel-child-content-child-summary-errors .error-message").get_by_text(
            "This field is required"
        )
    ).to_be_visible()

    expect(
        context.page.locator(
            "#panel-child-content-child-metadata-child-panel-child-publication_date-errors .error-message"
        ).get_by_text("This field is required")
    ).to_be_visible()

    expect(context.page.locator(".help-block.help-critical").get_by_text("This field is required")).to_be_visible()


@then("the preview of the methodology page is displayed with the populated data")
def preview_is_visible(context: Context) -> None:
    context.page.get_by_role("button", name="Toggle preview").click()

    iframe_locator = context.page.frame_locator("#w-preview-iframe")

    expect(iframe_locator.get_by_role("heading", name="Methodology page")).to_be_visible()
    expect(iframe_locator.get_by_text("Page summary")).to_be_visible()
    expect(iframe_locator.get_by_text("1 January 1950", exact=True)).to_be_visible()
    expect(iframe_locator.get_by_role("heading", name="Cite this methodology")).to_be_visible()
    expect(iframe_locator.get_by_role("heading", name="Heading")).to_be_visible()
    expect(iframe_locator.get_by_role("heading", name="Content")).to_be_visible()


@then("the preview of the methodology page matches the populated data")
def saved_draft_data_matches_populated_data(context: Context) -> None:
    context.page.get_by_role("button", name="Actions").click()
    context.page.get_by_role("link", name="Preview", exact=True).click()
    the_methodology_page_is_displayed_with_the_populated_data(context)
