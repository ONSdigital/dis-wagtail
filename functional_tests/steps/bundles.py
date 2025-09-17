from datetime import timedelta

from behave import given, step, then  # pylint: disable=no-name-in-module
from behave.runner import Context
from django.urls import reverse
from django.utils import timezone
from playwright.sync_api import expect

from cms.bundles.enums import BundleStatus
from cms.bundles.models import BundleTeam
from cms.bundles.tests.factories import BundleFactory
from cms.release_calendar.tests.factories import ReleaseCalendarPageFactory
from cms.teams.models import Team
from cms.users.tests.factories import UserFactory


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


@then('the selected datasets are displayed in the "Data API datasets" section')
def the_selected_datasets_are_displayed(context: Context) -> None:
    context.page.get_by_role("heading", name="Dataset 1").is_visible()
    context.page.get_by_text("Looked up dataset (Edition: Example Dataset 1, Ver: 1)").is_visible()
    context.page.get_by_role("heading", name="Dataset 2").is_visible()
    context.page.get_by_text(
        "Personal well-being estimates by local authority (Edition: Example Dataset 2, Ver: 1)"
    ).is_visible()
    context.page.get_by_role("heading", name="Dataset 3").is_visible()
    context.page.get_by_text(
        "Deaths registered weekly in England and Wales by region (Edition: Example Dataset 3, Ver: 1)"
    ).is_visible()


# bundle create amend
@step("a bundle has been created with a creator")
def a_bundle_has_been_created_with_user(context: Context) -> None:
    context.bundle_creator = UserFactory()
    context.bundle = BundleFactory(created_by=context.bundle_creator)


@step("the bundle has creator removed")
def delete_bundle_creator(context: Context) -> None:
    context.bundle_creator.delete()


# bundle goto
@step("the user goes to the bundle inspect page")
def go_to_bundle_inspect(context: Context) -> None:
    context.page.goto(context.base_url + reverse("bundle:inspect", args=[context.bundle.pk]))


@step("the user goes to the bundle menu page")
def go_to_bundle_menu(context: Context) -> None:
    context.page.goto(context.base_url + reverse("bundle:index"))


# bundle Menu
@step("the bundle menu shows bundle and Added by is not empty")
def bundle_menu_contains_value(
    context: Context,
) -> None:
    expect(context.page.get_by_role("table")).to_contain_text(context.bundle.name)
    expect(context.page.get_by_role("table")).to_contain_text(context.bundle_creator.get_full_name())


@step("the bundle menu shows bundle and Added by is empty")
def bundle_menu_does_not_contain_value(context: Context) -> None:
    expect(context.page.get_by_role("table")).to_contain_text(context.bundle.name)
    expect(context.page.get_by_role("table")).not_to_contain_text(context.bundle_creator.get_full_name())


# bundle Inspect
@step("the user can inspect Bundle details and Created by is not empty")
def the_user_can_see_the_bundle_details_with_creator(context: Context) -> None:
    expect(context.page.get_by_text("Created by")).to_be_visible()
    expect(context.page.get_by_text(context.bundle_creator.get_username())).to_be_visible()


@step("the user can inspect Bundle details and Created by is empty")
def bundle_inspect_show(context: Context) -> None:
    expect(context.page.get_by_text("Created by")).to_be_visible()
    expect(context.page.get_by_text(context.bundle_creator.get_username())).not_to_be_visible()


@given("a Release Calendar with a release date in the future exists")
def create_future_release_calendar_page(context: Context) -> None:
    tomorrow = timezone.now() + timedelta(days=1)
    context.release_calendar_page = ReleaseCalendarPageFactory(
        title="Future Release Calendar Page",
        release_date=tomorrow,
    )
    context.release_calendar_page.save_revision().save()


@step("the user adds a title to the bundle")
def user_adds_title_to_bundle(context: Context) -> None:
    context.page.get_by_role("textbox", name="Name*").fill("Test Bundles")


@step("the user selects a release calendar page through the chooser")
def user_schedules_future_release_calendar_page(context: Context) -> None:
    the_user_selects_a_release_calendar(context)
    context.page.get_by_text("Future Release Calendar Page").click()


@step("the user saves the bundle")
def user_saves_bundle(context: Context) -> None:
    context.page.get_by_role("button", name="Save as draft").click()


@step("the user sees the release calendar page title, status and release date")
def release_calendar_page_panel_displays_status_and_release_date(
    context: Context,
) -> None:
    expect(
        context.page.get_by_text(
            f"Future Release Calendar Page ({context.release_calendar_page.status},"
            f" {context.release_calendar_page.release_date_value})"
        )
    )


@then("the user updates the release calendar page details, after it has been selected")
def user_updates_release_calendar_page_details(context: Context) -> None:
    context.page.get_by_role("region", name="Scheduling").get_by_label("Actions").click()
    with context.page.expect_popup() as edit_release_calendar_page:
        context.page.get_by_role("link", name="Edit Release Calendar page").click()
    # closes original bundles edit view
    context.page.close()
    # assigns context to new release calendar page edit view
    context.page = edit_release_calendar_page.value

    # tracks original release calendar details
    context.original_date = context.release_calendar_page.release_date_value
    context.original_title = context.release_calendar_page.title
    context.original_status = context.release_calendar_page.status

    # enter new details
    context.page.get_by_placeholder("Page title*").fill("New title")
    context.page.get_by_label("Status*").select_option("CONFIRMED")
    new_date = timezone.now() + timedelta(days=1)
    formatted_date = new_date.strftime("%Y-%m-%d %H:%M")
    context.page.get_by_role("textbox", name="Release date*").fill(formatted_date)
    context.page.get_by_role("button", name="Save draft").click()


@step("returns to the bundle with this release calendar page assigned")
def user_returns_to_bundle_page_release_calendar_page_was_assigned_to(
    context: Context,
) -> None:
    with context.page.expect_popup() as bundle_admin_view:
        context.page.locator("#panel-child-content-metadata-content").get_by_role("link", name="Bundle").click()
    # closes release calendar page edit view
    context.page.close()
    # assigns context to new bundles edit view
    context.page = bundle_admin_view.value


@then("the user sees the release calendar page with the updated details")
def release_calendar_page_panel_displays_updated_status_and_release_date(
    context: Context,
) -> None:
    expect(context.page.get_by_text(f"New title (CONFIRMED, {context.release_calendar_page.release_date_value}))"))
    expect(
        context.page.get_by_text(f"{context.original_title} ({context.original_status}, {context.original_date})")
    ).not_to_be_visible()
