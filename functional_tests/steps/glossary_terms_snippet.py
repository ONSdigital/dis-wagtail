from behave import then, when  # pylint: disable=no-name-in-module
from behave.runner import Context
from playwright.sync_api import expect


@when("the user adds a Glossary Terms snippet")
def user_adds_glossary_terms_snippet(context: Context) -> None:
    context.page.get_by_role("link", name="Snippets").click()
    context.page.get_by_role("link", name="Glossary terms").click()
    context.page.get_by_role("link", name="Add glossary term").click()
    context.page.get_by_role("textbox", name="Title*").click()
    context.page.get_by_role("textbox", name="Title*").fill("Term")
    context.page.get_by_role("region", name="Definition*").get_by_role("textbox").click()
    context.page.get_by_role("region", name="Definition*").get_by_role("textbox").fill("Definition")
    context.page.get_by_role("button", name="Save").click()


@then("the Glossary Term is added to the list")
def glossary_item_is_visible_in_index_view_with_the_required_columns(context: Context) -> None:
    expect(context.page.get_by_role("cell", name="Term")).to_be_visible()


@then("the Updated time is displayed")
def the_last_edited_time_column_is_displayed(context: Context) -> None:
    expect(context.page.get_by_role("cell", name="Just now")).to_be_visible()


@then("the Updated by field is populated with the user's name")
def the_edited_by_column_is_displayed(context: Context) -> None:
    expect(context.page.get_by_role("cell", name=context.full_name)).to_be_visible()
