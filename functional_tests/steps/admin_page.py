# pylint: disable=not-callable
import re

from behave import step, then, when
from behave.runner import Context
from playwright.sync_api import expect


@step("the user can see the {menu_item} menu item")
def the_user_can_see_reports_menu_item(context: Context, menu_item: str) -> None:
    role = "button" if menu_item in ("Reports", "Pages", "Settings") else "link"
    expect(context.page.get_by_role(role, name=menu_item, exact=True)).to_be_visible()


@when("the user clicks the {menu_item} menu item")
def user_clicks_the_menu_item(context: Context, menu_item: str) -> None:
    role = "button" if menu_item in ("Reports", "Pages", "Settings") else "link"
    context.page.get_by_role(role, name=menu_item, exact=True).click()


@then("the user can inspect bundle details")
def the_user_can_see_the_bundle_details(context: Context) -> None:
    context.page.get_by_role("link", name="Bundles", exact=True).click()
    context.page.get_by_role("link", name=f"Inspect '{context.bundle.name}'").click()


@then("the user can add {object_name} snippet")
def the_user_can_see_snippet(context: Context, object_name: str) -> None:
    context.page.get_by_role("link", name=object_name).click()
    expect(context.page.get_by_role("link", name=re.compile("Add*"))).to_be_visible()


@then("the user can add Bundles")
def the_user_can_add_bundles(context: Context) -> None:
    expect(context.page.get_by_role("link", name="Add bundle")).to_be_visible()


@then("the user can create and publish the {snippet_name} snippet")
def the_user_can_create_and_publish_snippet(context: Context, snippet_name: str) -> None:
    context.page.get_by_role("link", name=snippet_name).click()
    context.page.get_by_role("link", name=re.compile("Add*")).click()

    expect(context.page.get_by_role("button", name="Save draft")).to_be_visible()
    context.page.get_by_role("button", name="More actions").click()
    expect(context.page.get_by_role("button", name="Publish")).to_be_visible()
