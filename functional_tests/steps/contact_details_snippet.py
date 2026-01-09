# pylint: disable=not-callable
from behave import given, then, when
from behave.runner import Context
from playwright.sync_api import expect

from cms.core.tests.factories import ContactDetailsFactory


@given("a contact details snippet exists")
def create_contact_details_snippet(context: Context) -> None:
    context.contact_details_snippet = ContactDetailsFactory()


@given("a contact detail for John Doe exists")
def create_john_doe_contact_details(context: Context) -> None:
    context.contact_details_snippet = ContactDetailsFactory(
        name="John Doe",
        email="john.doe@example.com",
        phone="020 7946 0958",
    )


@given("a contact detail for Jane Smith exists")
def create_jane_smith_contact_details(context: Context) -> None:
    context.jane_smith_contact_details = ContactDetailsFactory(
        name="Jane Smith",
        email="jane.smith@example.com",
        phone="020 7123 4567",
    )


@when('a user goes to the "{snippet_name}" snippet listing page')
def navigate_to_snippet_listing(context: Context, snippet_name: str) -> None:
    context.page.get_by_role("link", name="Snippets").click()
    context.page.get_by_role("link", name=snippet_name).click()


@when('the user clicks the "{link_text}" link')
def click_button(context: Context, link_text: str) -> None:
    context.page.get_by_role("link", name=link_text).click()


@when("the user fills in the contact details form with valid data")
def fill_contact_details_form_with_valid_data(context: Context) -> None:
    context.page.get_by_role("textbox", name="Name*").fill("Jane Smith")
    context.page.get_by_role("textbox", name="Email*").fill("jane.smith@example.com")
    context.page.get_by_role("textbox", name="Phone").fill("020 7123 4567")


@when("the user fills in the contact details form with John Doe's details")
def fill_contact_details_form_with_john_doe_details(context: Context) -> None:
    context.page.get_by_role("textbox", name="Name*").fill("John Doe")
    context.page.get_by_role("textbox", name="Email*").fill("john.doe@example.com")
    context.page.get_by_role("textbox", name="Phone").fill("020 7946 0958")


@when("the user submits the contact details form")
def submit_contact_details_form(context: Context) -> None:
    context.page.get_by_role("button", name="Save").click()


@when('the user clicks the "Edit" button for {name}\'s contact details')
def click_edit_for_contact(context: Context, name: str) -> None:
    context.page.get_by_role("link", name=name).click()


@when("the user updates the phone number")
def update_phone_number(context: Context) -> None:
    context.page.get_by_role("textbox", name="Phone").fill("020 9876 5432")


@when("the user updates the name and email to match John Doe's details")
def update_name_and_email_to_john_doe(context: Context) -> None:
    context.page.get_by_role("textbox", name="Name*").fill("John Doe")
    context.page.get_by_role("textbox", name="Email*").fill("john.doe@example.com")


@then("the user sees a success message indicating the contact details snippet was created")
def verify_creation_success_message(context: Context) -> None:
    expect(context.page.get_by_text("Contact details 'Jane Smith' created.")).to_be_visible()


@then("the user sees an error message indicating a duplicate contact details snippet cannot be created")
def verify_duplicate_error_message(context: Context) -> None:
    expect(
        context.page.get_by_text("Contact details with this name and email combination already exists.")
    ).to_be_visible()


@then("the user sees a success message indicating the contact details snippet was updated")
def verify_update_success_message(context: Context) -> None:
    expect(context.page.get_by_text("Contact details 'John Doe' updated.")).to_be_visible()
