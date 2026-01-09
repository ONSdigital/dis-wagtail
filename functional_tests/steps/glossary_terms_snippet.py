# pylint: disable=not-callable
from behave import given, step, then, when
from behave.runner import Context
from playwright.sync_api import expect

from cms.core.models import GlossaryTerm


@step("the user adds another Glossary Terms snippet with the same name")
@step("the user adds a Glossary Terms snippet")
def user_adds_glossary_terms_snippet(context: Context) -> None:
    user_fills_in_glossary_term_details(context)
    context.page.get_by_role("button", name="Save").click()


@given("the user fills in Glossary Term details")
def user_fills_in_glossary_term_details(context: Context) -> None:
    context.page.get_by_role("link", name="Snippets").click()
    context.page.get_by_role("link", name="Glossary terms").click()
    context.page.get_by_role("link", name="Add glossary term").click()
    context.page.get_by_role("textbox", name="Name*").fill("Term")
    context.page.get_by_role("region", name="Definition*").get_by_role("textbox").fill("Definition")
    context.page.get_by_role("button", name="Choose a user").click()
    context.page.get_by_role("link", name=context.user_data["full_name"]).first.click()


@given("a Glossary Terms snippet exists")
def a_glossary_terms_snippet_exists(context: Context) -> None:
    context.glossary_term = GlossaryTerm.objects.create(name="Term", definition="Definition")


@then("a validation error is displayed")
def validation_error_is_displayed_for_duplicated_glossary_terms(
    context: Context,
) -> None:
    expect(context.page.get_by_text("The glossary term could not be created due to errors.")).to_be_visible()


@then("the Glossary Term is added to the list")
def glossary_item_is_visible_in_index_view_with_the_required_columns(
    context: Context,
) -> None:
    expect(context.page.get_by_role("columnheader", name="Name")).to_contain_text("Name")
    expect(context.page.locator("tr:nth-child(1) > td:nth-child(2)")).to_contain_text("Term")


@then("the Updated time is displayed")
def the_last_edited_time_column_is_displayed(context: Context) -> None:
    expect(context.page.get_by_role("columnheader", name="Updated", exact=True)).to_contain_text("Updated")
    expect(context.page.locator("tr:nth-child(1) > td:nth-child(4)")).to_contain_text("Just now")


@then("the Updated by field is populated with the user's name")
def the_edited_by_column_is_displayed(context: Context) -> None:
    expect(context.page.get_by_role("columnheader", name="Updated by")).to_contain_text("Updated by")
    expect(context.page.locator("tr:nth-child(1) > td:nth-child(5)")).to_contain_text(context.user_data["full_name"])


@then("the Owner field is populated with the user's name")
def owner_field_has_the_correct_user(context: Context) -> None:
    expect(context.page.get_by_role("columnheader", name="Owner")).to_contain_text("Owner")
    expect(context.page.locator("tr:nth-child(1) > td:nth-child(6)")).to_contain_text(context.user_data["full_name"])


@given("the user modifies the Glossary Term description")
def user_edits_glossary_term(context: Context) -> None:
    context.page.get_by_role("link", name="Term", exact=True).click()
    context.page.get_by_role("region", name="Definition*").get_by_role("textbox").fill("Edited definition")
    context.page.get_by_role("button", name="Save").click()


@when("the user navigates to the snippet history menu")
def the_user_navigates_to_the_page_history_menu(context: Context) -> None:
    context.page.get_by_role("link", name="Term", exact=True).click()
    context.page.get_by_role("link", name="History").click()


@then("the past revisions of the snippet are displayed")
def the_past_revisions_are_visible(context: Context) -> None:
    expect(context.page.get_by_role("cell", name="Created")).to_be_visible()
    expect(context.page.get_by_role("cell", name=context.user_data["full_name"]).nth(1)).to_be_visible()
    expect(context.page.get_by_role("cell", name="Just now").nth(1)).to_be_visible()

    expect(context.page.get_by_role("cell", name="Edited")).to_be_visible()
    expect(context.page.get_by_role("cell", name=context.user_data["full_name"]).first).to_be_visible()
    expect(context.page.get_by_role("cell", name="Just now").first).to_be_visible()


@then("the user can see the Glossary Term in the preview tab")
def the_glossary_term_is_visible_in_preview_tab(context: Context) -> None:
    iframe_locator = context.page.frame_locator("#w-preview-iframe")
    expect(iframe_locator.get_by_role("link", name="Term")).to_be_visible()
    expect(iframe_locator.get_by_text("Definition", exact=True)).to_be_hidden()


@then("the user can click the Glossary Term to see the definition in the preview tab")
def the_glossary_term_definition_is_visible_in_preview_tab(context: Context) -> None:
    iframe_locator = context.page.frame_locator("#w-preview-iframe")
    iframe_locator.get_by_role("link", name="Term").click()
    expect(iframe_locator.get_by_text("Definition", exact=True)).to_be_visible()


@then("the user can see the Glossary Term")
def the_user_can_see_the_preview_of_the_glossary_term(context: Context) -> None:
    expect(context.page.get_by_text("Term", exact=True)).to_be_visible()
    expect(context.page.get_by_text("Definition", exact=True)).to_be_hidden()


@then("the user can click the Glossary Term to see the definition")
def the_user_clicks_the_glossary_term_to_see_the_definition(context: Context) -> None:
    context.page.get_by_role("link", name="Term").click()
    expect(context.page.get_by_text("Definition", exact=True)).to_be_visible()
