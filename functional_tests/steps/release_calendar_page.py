from behave import given, step, then, when  # pylint: disable=no-name-in-module
from behave.runner import Context
from django.urls import reverse
from playwright.sync_api import expect

from cms.release_calendar.tests.factories import ReleaseCalendarPageFactory


@given("a Release Calendar page with a published notice exists")
def create_release_calendar_page(context: Context):
    context.release_calendar_page = ReleaseCalendarPageFactory(
        notice="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
    )
    context.release_calendar_page.save_revision().publish()


@given("the user navigates to the release calendar page")
def navigate_to_release_page(context: Context):
    context.page.get_by_role("button", name="Pages").click()
    context.page.get_by_role("link", name="View child pages of 'Home'").click()
    context.page.get_by_role("link", name="Release calendar", exact=True).click()


@when('the user clicks "Add child page" to create a new draft release page')
def click_add_child_page(context: Context):
    context.page.get_by_label("Add child page").click()


@when("the user navigates to the published release calendar page")
def navigate_to_published_release_page(context: Context):
    edit_url = reverse("wagtailadmin_pages:edit", args=(context.release_calendar_page.id,))
    context.page.goto(f"{context.base_url}{edit_url}")


@step("the user returns to editing the release page")
def user_returns_to_editing_the_release_page(context: Context):
    context.page.get_by_role("link", name="Edit").click()


# Page creation, status and preview modes


@step('the user sets the page status to "{page_status}"')
def set_page_status(context: Context, page_status: str):
    context.page.get_by_label("Status*").select_option(page_status.upper())


@when('the user enters "Published" page content')
@when('the user enters "Provisional" page content')
@when('the user enters "Confirmed" page content')
@when("the user enters some example content on the page")
def user_enters_example_release_content(context: Context):
    page = context.page
    page.get_by_placeholder("Page title*").fill("My Release")

    page.get_by_role("textbox", name="Release date*").fill("2024-12-25")
    page.get_by_role("textbox", name="Release date*").press("Enter")

    page.get_by_role("region", name="Summary*").get_by_role("textbox").fill("My example release page")

    page.locator("#panel-child-content-content-content").get_by_role("button", name="Insert a block").click()
    page.get_by_role("region", name="Release content").get_by_label("Title*").fill("My Example Content Link")

    page.get_by_role("button", name="Choose a page").click()
    page.get_by_label("Explore").click()
    page.get_by_role("link", name="Release calendar").click()

    page.get_by_label("Accredited Official Statistics").check()


@when('the user enters "Cancelled" page content')
def user_enters_cancelled_release_content(context: Context):
    context.page.locator(".public-DraftStyleDefault-block").first.fill("Notice cancelled")
    user_enters_example_release_content(context)


@when("the user adds contact detail")
def user_adds_contact_detail(context: Context):
    context.page.get_by_role("button", name="Choose contact details").click()
    context.page.get_by_role("link", name=context.contact_details_snippet.name).click()


@then("contact detail is displayed")
def displayed_contact_details(context: Context):
    page = context.preview_page
    expect(page.get_by_role("heading", name="Contact details")).to_be_visible()
    expect(page.get_by_text(context.contact_details_snippet.name)).to_be_visible()
    expect(page.get_by_role("link", name=context.contact_details_snippet.email)).to_be_visible()


@then('the page status is set to "Provisional" and the release date text field is visible')
def check_that_default_status_is_provisional_and_release_date_text_is_visible(
    context: Context,
):
    expect(context.page.get_by_label("Status*")).to_have_value("PROVISIONAL")
    expect(context.page.get_by_text("Or, release date text")).to_be_visible()


@when('the user changes preview mode to "{page_status}"')
def user_changes_preview_mode(context: Context, page_status: str):
    context.page.get_by_label("Preview mode").select_option(page_status)


@when("the preview tab is opened")
def open_preview_tab(context: Context):
    context.page.get_by_role("link", name="Preview in new tab").click()

    with context.page.expect_popup() as page1_info:
        context.page.get_by_role("link", name="Preview in new tab").click()
    context.preview_page = page1_info.value


@then('the "Provisional" page is displayed')
def display_provisional_release_page(context: Context):
    expect(context.page.get_by_text("This release is not yet")).to_be_visible()


@then('the "Provisional" page is displayed in the preview tab')
def preview_provisional_release_page(context: Context):
    expect(context.preview_page.get_by_text("This release is not yet")).to_be_visible()


@then('the "Confirmed" page is displayed in the preview tab')
def preview_confirmed_release_page(context: Context):
    expect(context.preview_page.get_by_text("This release is not yet")).to_be_visible()


@then('the "Published" page is displayed in the preview tab')
def preview_published_release_page(context: Context):
    page = context.preview_page
    expect(page.get_by_role("heading", name="My Release")).to_be_visible()
    expect(page.get_by_role("heading", name="My Example Content Link")).to_be_visible()
    expect(page.locator("#my-example-content-link").get_by_role("link", name="Release calendar")).to_be_visible()
    expect(page.get_by_text("Accredited Official Statistics", exact=True)).to_be_visible()


@then('the "Cancelled" page is displayed in the preview tab')
def preview_cancelled_page(context: Context):
    expect(context.preview_page.get_by_text("Cancelled", exact=True)).to_be_visible()


@then('the "Confirmed" page is displayed')
def display_confirmed_page(context: Context):
    expect(context.page.get_by_text("This release is not yet")).to_be_visible()


@then('the "Published" page is displayed')
def display_published_page(context: Context):
    page = context.page
    expect(page.get_by_role("heading", name="My Release")).to_be_visible()
    expect(page.get_by_role("heading", name="My Example Content Link")).to_be_visible()
    expect(page.locator("#my-example-content-link").get_by_role("link", name="Release calendar")).to_be_visible()
    expect(page.get_by_text("Accredited Official Statistics", exact=True)).to_be_visible()


@then('the "Cancelled" page is displayed')
def display_cancelled_page(context: Context):
    expect(context.page.get_by_text("Cancelled", exact=True)).to_be_visible()
    expect(context.page.get_by_text("Notice cancelled")).to_be_visible()


@when("the user adds related link")
def user_adds_related_links(context: Context):
    context.page.locator("#panel-child-content-related_links-content").get_by_role(
        "button", name="Insert a block"
    ).click()
    context.page.get_by_role("button", name="Choose a page").click()
    context.page.get_by_role("link", name="Home").click()


@then("related link is displayed")
def displayed_related_links(context: Context):
    expect(context.preview_page.get_by_role("heading", name="You might also be interested")).to_be_visible()
    expect(context.preview_page.locator("#links").get_by_role("link", name="Home")).to_be_visible()


@then("the release date change is displayed")
def displayed_date_change_log(context: Context):
    expect(context.preview_page.get_by_text("Updated due to data availability")).to_be_visible()


# Notice


@then("the notice field is disabled")
def check_notice_field_disabled(context: Context):
    expect(context.page.locator('[name="notice"]')).to_be_disabled()


@then("an error message is displayed describing notice must be added")
def error_cancelled_notice_must_be_added(context: Context):
    expect(context.page.get_by_text("The page could not be created")).to_be_visible()
    expect(context.page.get_by_text("The notice field is required")).to_be_visible()


# Pre-release access


@when("the user adds pre-release access information")
def user_adds_pre_release_access(context: Context):
    page = context.page
    # Table
    page.locator("#panel-child-content-pre_release_access-content").get_by_role("button", name="Insert a block").click()
    page.get_by_text("Basic table").click()
    page.get_by_label("Table headers").select_option("column")
    page.get_by_role("textbox", name="Table caption").click()
    page.get_by_role("textbox", name="Table caption").fill("Caption")
    page.locator("td").first.click()
    page.keyboard.type("first")
    page.locator("td:nth-child(2)").first.click()
    page.keyboard.type("second")

    # Description
    page.locator("#panel-child-content-pre_release_access-content").get_by_role("button", name="Insert a block").nth(
        1
    ).click()
    page.get_by_role("option", name="Description").click()
    page.get_by_role("region", name="Description *").get_by_role("textbox").fill("Description")


@then("pre-release access information is displayed")
def displayed_pre_release_access(context: Context):
    page = context.preview_page
    expect(page.get_by_text("Pre-release access list")).to_be_visible()
    expect(page.get_by_text("first")).to_be_visible()
    expect(page.get_by_text("second")).to_be_visible()
    expect(page.get_by_text("Description")).to_be_visible()


@when("multiple descriptions are added under pre-release access")
def user_adds_multiple_descriptions_to_pre_release_access(context: Context):
    context.page.locator("#panel-child-content-pre_release_access-content").get_by_role(
        "button", name="Insert a block"
    ).click()
    context.page.get_by_role("option", name="Description").click()
    context.page.locator("#panel-child-content-pre_release_access-content").get_by_role(
        "button", name="Insert a block"
    ).nth(2).click()
    context.page.get_by_role("option", name="Description").click()


@then("an error message is displayed about the descriptions")
def error_multiple_description(context: Context):
    expect(context.page.get_by_text("Description: The maximum")).to_be_visible()


@when("multiple tables are added under pre-release access")
def user_adds_multiple_tables_to_pre_release_access(context: Context):
    context.page.locator("#panel-child-content-pre_release_access-content").get_by_role(
        "button", name="Insert a block"
    ).click()
    context.page.get_by_text("Basic table").click()
    context.page.locator("#panel-child-content-pre_release_access-content").get_by_role(
        "button", name="Insert a block"
    ).nth(1).click()
    context.page.locator("#downshift-7-item-1").get_by_text("Basic table").click()


@then("an error message is displayed about the tables")
def error_multiple_tables(context: Context):
    expect(context.page.get_by_text("Basic table: The maximum")).to_be_visible()


@then("an error message is displayed to select and option")
def error_unpicked_table_option(context: Context):
    expect(context.page.get_by_text("The page could not be saved")).to_be_visible()
    expect(context.page.get_by_text("Select an option for Table")).to_be_visible()


@then("an error message is displayed about empty table")
def error_empty_table(context: Context):
    expect(context.page.get_by_text("The page could not be saved")).to_be_visible()
    expect(context.page.get_by_text("The table cannot be empty")).to_be_visible()
