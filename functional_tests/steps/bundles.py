import datetime

from behave import step  # pylint: disable=no-name-in-module
from behave.runner import Context
from cms.users.models import User

from cms.bundles.enums import BundleStatus
from cms.bundles.models import BundleTeam
from cms.bundles.tests.factories import BundleFactory
from cms.teams.models import Team
from playwright.sync_api import expect


@step("a bundle has been created")
def a_bundle_has_been_created(context: Context) -> None:
    context.bundle = BundleFactory()


@step("is ready for review")
def the_bundle_is_ready_for_review(context: Context) -> None:
    context.bundle.status = BundleStatus.IN_REVIEW
    context.bundle.save(update_fields=["status"])


@step("has a preview team")
def a_bundle_has_a_preview_team(context: Context) -> None:
    context.team = Team.objects.create(identifier="preview-team", name="Preview team")
    BundleTeam.objects.create(parent=context.bundle, team=context.team)


@step("the viewer is in the preview team")
def the_viewer_is_in_the_preview_team(context: Context) -> None:
    user = context.user_data["user"]
    user.teams.add(context.team)


@step("the user goes to the bundle creation page")
def the_user_goes_to_the_bundle_creation_page(context: Context) -> None:
    context.page.goto(context.base_url + "/admin/bundle/new/")


@step("the user opens the release calendar page chooser")
def the_user_selects_a_release_calendar(context: Context) -> None:
    context.page.get_by_role("button", name="Choose Release Calendar page").click()
    context.page.wait_for_timeout(250)  # Wait for the modal to open


@step("the user opens the page chooser")
def the_user_opens_page_chooser(context: Context) -> None:
    context.page.get_by_role("button", name="Add page").click()
    context.page.wait_for_timeout(100)
    context.page.get_by_role("button", name="Choose a page").click()
    context.page.wait_for_timeout(250)  # Wait for the modal to open


@step("the locale column is displayed in the chooser")
def the_locale_column_is_displayed(context: Context) -> None:
    modal = context.page.locator(".modal-body")
    modal.get_by_role("columnheader", name="Locale").is_visible()

@step('the user can inspect Bundle details with name "{bundle_name}" and creator "{creator}"')
def the_user_can_see_the_bundle_details_with_creator(context: Context, bundle_name: str, creator: str) -> None:
    expect(context.page.get_by_text("Created by")).to_be_visible()
    expect(context.page.get_by_text(creator)).to_be_visible()

@step('a bundle has been created with name "{bundle_name}" and creator "{creator}"')
def a_bundle_has_been_created(context: Context, bundle_name: str, creator: str) -> None:
    context.user = User.objects.create_user(username=creator,email= "email@example.com",password= "password",first_name= "first_Name",last_name= "Last_Name")
    context.bundle = BundleFactory(name = bundle_name, created_by = context.user )

@step('the bundle menu shows bundle with name "{bundle_name}" and creator "{creator}"')
def bundle_menu_show(context: Context, bundle_name: str, creator: str) -> None:
    context.page.goto(context.base_url + "/admin/bundle/")
    if hasattr(context, 'user'):
        fullname = context.user.get_full_name()
    else:
        fullname = context.user_data["full_name"]
    expect(context.page.get_by_role("table")).to_contain_text(bundle_name)
    expect(context.page.get_by_role("table")).to_contain_text(fullname)

@step('the user goes to the bundle inspect page with name "{bundle_name}"')
def go_to_bundle_inspect(context: Context, bundle_name: str) -> None:
    context.page.goto(context.base_url + "/admin/bundle/inspect/1/")

@step('the bundle has creator removed')
def delete_bundle_creator(context: Context) -> None:
        context.bundle.created_by = None
        context.bundle.save(update_fields=["created_by"])

@step('the bundle menu shows bundle with name "{bundle_name}" and no creator')
def bundle_menu_show(context: Context, bundle_name: str) -> None:
    if hasattr(context, 'user'):
        fullname = context.user.get_full_name()
    else:
        fullname = context.user_data["full_name"]

    context.page.goto(context.base_url + "/admin/bundle/")
    expect(context.page.get_by_role("table")).to_contain_text(bundle_name)
    expect(context.page.get_by_role("table")).not_to_contain_text(fullname)

@step('the user can inspect Bundle details with name "{bundle_name}" and creator has no entry')
def bundle_inspect_show(context: Context, bundle_name: str) -> None:
    expect(context.page.get_by_text("Created by")).to_be_visible()
    expect(context.page.get_by_text(context.user.get_username())).not_to_be_visible();
