# pylint: disable=not-callable

import json
import re
from datetime import datetime, time, timedelta
from typing import Literal

from behave import given, step, then, when
from behave.runner import Context
from django.urls import reverse
from django.utils import timezone
from playwright.sync_api import expect

from cms.articles.tests.factories import ArticleSeriesPageFactory, StatisticalArticlePageFactory
from cms.bundles.enums import BundleStatus
from cms.bundles.models import BundlePage, BundleTeam
from cms.bundles.tests.factories import BundleFactory
from cms.core.custom_date_format import ons_date_format
from cms.release_calendar.enums import ReleaseStatus
from cms.release_calendar.tests.factories import ReleaseCalendarPageFactory
from cms.teams.models import Team
from cms.users.tests.factories import UserFactory
from cms.workflows.tests.utils import mark_page_as_ready_to_publish
from functional_tests.step_helpers.users import create_user
from functional_tests.step_helpers.utils import get_page_from_context
from functional_tests.steps.release_page import click_add_child_page, navigate_to_release_calendar_page

tomorrow = timezone.now() + timedelta(days=1)


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


@step("the user navigates to the bundle creation page")
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


@then("the selected datasets are displayed in the inspect view")
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


@step("the user clicks on the inspect link for the created bundle")
def user_clicks_on_inspect_link_for_created_bundle(context: Context) -> None:
    # This is a different approach when bundle does not exist in the context
    context.page.locator("#w-slim-header-buttons").get_by_role("button", name="Actions").click()
    context.page.get_by_role("link", name="Inspect", exact=True).click()


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


@step("the user saves the bundle as draft")
def user_saves_bundle_as_draft(context: Context) -> None:
    context.page.get_by_role("button", name="Save as Draft").click()


@step("the user sets the bundle title")
def user_sets_bundle_title(context: Context) -> None:
    context.page.get_by_role("textbox", name="Name*").fill("Test Bundle")


@step("the user opens the preview for one of the selected datasets")
def user_opens_preview_for_one_of_the_selected_datasets(context: Context) -> None:
    context.page.get_by_role("link", name="Preview", exact=True).nth(0).click()


@step("the user can see the preview items dropdown")
def user_can_see_preview_items_dropdown(context: Context) -> None:
    # Ensure we look for a select element with the specific id to avoid false positives
    context.page.locator("select#preview-items").is_visible()


# bundle Inspect
@step("the user can inspect Bundle details and Created by is not empty")
def the_user_can_see_the_bundle_details_with_creator(context: Context) -> None:
    expect(context.page.get_by_text("Created by")).to_be_visible()
    expect(context.page.get_by_text(context.bundle_creator.get_username())).to_be_visible()


@step("the user can inspect Bundle details and Created by is empty")
def bundle_inspect_show(context: Context) -> None:
    expect(context.page.get_by_text("Created by")).to_be_visible()
    expect(context.page.get_by_text(context.bundle_creator.get_username())).not_to_be_visible()


# To test release calendar page panel
@given("a release calendar page with a future release date exists")
@given('a release calendar page with a "{status}" status and future release date exists')
def release_calendar_page_with_status_and_future_date_exists(context: Context, status: str = "Provisional") -> None:
    context.release_calendar_page = ReleaseCalendarPageFactory(
        release_date=tomorrow,
        status=status.upper(),
        notice="default notice",
    )
    context.release_calendar_page.save_revision().save()


@step('the user manually creates a future release calendar page with a "{status}" status')
def user_manually_creates_future_release_calendar(context: Context, status: str) -> None:
    navigate_to_release_calendar_page(context)
    click_add_child_page(context)
    title = "Future Release Calendar Page"
    context.page.get_by_placeholder("Page title*").fill(title)
    context.page.get_by_label("Status*").select_option(status.upper())
    formatted_date = tomorrow.strftime("%Y-%m-%d %H:%M")
    context.page.get_by_role("textbox", name="Release date*").fill(formatted_date)
    context.page.get_by_role("region", name="Summary*").get_by_role("textbox").fill("My example release page")

    # Save the values to access later
    context.saved_release_calendar_page_details = {
        "title": title,
        "release_date_value": ons_date_format(tomorrow, "DATETIME_FORMAT"),
        "status": status,
    }


@when("the user enters a title")
def user_enters_title(context: Context) -> None:
    context.page.get_by_role("textbox", name="Name*").fill("Test Bundles")


@step("the user selects the existing release calendar page")
def user_creates_bundle_with_future_release_calendar_page(context: Context) -> None:
    try:
        title = context.release_calendar_page.title
    except AttributeError:
        title = context.saved_release_calendar_page_details["title"]

    context.page.get_by_text(title).click()


@step('the user clicks "Save as draft"')
def user_clicks_save_as_draft(context: Context) -> None:
    context.page.get_by_role("button", name="Save as draft").click()


@step("the user sees the release calendar page title, status and release date")
def user_sees_release_calendar_page_title_status_release_date(
    context: Context,
) -> None:
    expect(
        context.page.get_by_text(
            f"{context.release_calendar_page.title} ({context.release_calendar_page.status},"
            f" {context.release_calendar_page.release_date_value})"
        )
    ).to_be_visible()


@then('the user cannot see the "Cancelled" release calendar page')
def user_cannot_see_cancelled_release_calendar_page(context: Context) -> None:
    expect(context.page.get_by_text(context.release_calendar_page.title)).not_to_be_visible()


@step('the user updates the selected release calendar page\'s title, release date and sets the status to "{status}"')
def user_updates_selected_release_calendar_page_title_release_date_status(context: Context, status: str) -> None:
    day_after_tomorrow = timezone.localdate() + timedelta(days=2)

    # Set time to 10 am as using datetime.now() displayed an hour earlier than actual time for checking the updated time
    new_date = timezone.make_aware(datetime.combine(day_after_tomorrow, time(10, 0)), timezone.get_current_timezone())

    context.page.get_by_role("region", name="Scheduling").get_by_label("Actions").click()
    with context.page.expect_popup() as edit_release_calendar_page:
        context.page.get_by_role("link", name="Edit Release Calendar page").click()
    # closes original bundles edit view
    context.page.close()
    # assigns context to new release calendar page edit view
    context.page = edit_release_calendar_page.value
    # tracks original release calendar details
    context.original_date = context.saved_release_calendar_page_details["release_date_value"]
    context.original_title = context.saved_release_calendar_page_details["title"]
    context.original_status = context.saved_release_calendar_page_details["status"]

    if status == "Cancelled":
        context.page.locator("#panel-child-content-metadata-content div").filter(
            has_text="Cancellation notice Used for"
        ).get_by_role("textbox").fill("Cancelled notice")

    # enter new details
    context.page.get_by_placeholder("Page title*").fill("New title")
    context.page.get_by_label("Status*").select_option((status).upper())
    formatted_date = new_date.strftime("%Y-%m-%d %H:%M")
    context.page.get_by_role("textbox", name="Release date*").fill(formatted_date)
    context.page.get_by_role("button", name="Save draft").click()
    # tracks new release date with ons date format
    context.saved_release_calendar_page_details["release_date_value"] = ons_date_format(new_date, "DATETIME_FORMAT")


@step("returns to the bundle edit page")
def returns_to_bundle_edit_page(
    context: Context,
) -> None:
    with context.page.expect_popup() as bundle_admin_view:
        context.page.locator("#panel-child-content-metadata-content").get_by_role("link", name="Bundle").click()
    # closes release calendar page edit view
    context.page.close()
    # assigns context to new bundles edit view
    context.page = bundle_admin_view.value


@then('the user sees the updated release calendar page\'s title, release date and the status "{status}"')
def user_sees_updated_release_calendar_page_title_release_date_status(context: Context, status: str) -> None:
    expect(
        context.page.get_by_text(
            f"New title ({status}, {context.saved_release_calendar_page_details['release_date_value']})"
        )
    ).to_be_visible()
    expect(
        context.page.get_by_text(f"{context.original_title} ({context.original_status}, {context.original_date})")
    ).not_to_be_visible()


@step('the user tries to set the release calendar page status to "Cancelled"')
def user_tries_to_set_release_calendar_page_status_to_cancelled(context: Context) -> None:
    """Navigate to the release calendar page edit view and attempt to set status to Cancelled."""
    context.page.get_by_role("region", name="Scheduling").get_by_label("Actions").click()
    with context.page.expect_popup() as edit_release_calendar_page:
        context.page.get_by_role("link", name="Edit Release Calendar page").click()
    # Close original bundles edit view
    context.page.close()
    # Assign context to new release calendar page edit view
    context.page = edit_release_calendar_page.value

    # Fill in the notice field (required for cancellation)
    context.page.locator("#panel-child-content-metadata-content div").filter(
        has_text="Cancellation notice Used for"
    ).get_by_role("textbox").fill("Cancellation notice")

    # Set status to Cancelled
    context.page.get_by_label("Status*").select_option("CANCELLED")

    # Attempt to save the draft
    context.page.get_by_role("button", name="Save draft").click()


@then("the user sees a validation error preventing the cancellation because the page is in a bundle")
def user_sees_validation_error_preventing_cancellation(context: Context) -> None:
    """Verify that a validation error is shown preventing cancellation due to bundle membership."""
    expect(context.page.get_by_text("The page could not be saved due to validation errors")).to_be_visible()
    expect(
        context.page.get_by_text("Please unlink the release calendar page from the bundle before cancelling")
    ).to_be_visible()


@step('the {page_str} page is in a "{bundle_status}" bundle')
def the_page_is_in_the_given_bundle_with_status(
    context: Context, page_str: str, bundle_status: Literal["Draft", "In Preview", "Ready to publish", "Published"]
):
    the_page = get_page_from_context(context, page_str)
    bundle = getattr(context, "bundle", None)
    if not bundle:
        a_bundle_has_been_created(context)
        bundle = context.bundle

    match bundle_status.lower():
        case "in preview":
            status = BundleStatus.IN_REVIEW
        case "ready to publish":
            status = BundleStatus.APPROVED
        case "published":
            status = BundleStatus.PUBLISHED
        case _:
            status = BundleStatus.DRAFT

    bundle.status = status
    bundle.bundled_pages.add(BundlePage(page=the_page))
    bundle.save()


# Bundles UI Data Setup


@given("there is a {user_role} user")
def a_user_exists_by_role(context: Context, user_role: str) -> None:
    if not hasattr(context, "users"):
        context.users = {}
    context.users[user_role] = create_user(user_role)


@given("there is a statistical analysis page approved by {user_role}")
def statistical_analysis(context: Context, user_role: str) -> None:
    user = context.users[user_role]["user"]
    now = datetime.now()
    now -= timedelta(days=31)
    title = now.strftime("%B %Y")
    context.article_series_page = ArticleSeriesPageFactory(title="PSF", slug="PSF")
    article = StatisticalArticlePageFactory(parent=context.article_series_page, title=title, live=True, slug="edition")
    mark_page_as_ready_to_publish(article, user)
    article.save()
    context.statistical_article_page = article


@given("there is a release calendar page approved by {creator_role}")
def release_calendar(context: Context, creator_role: str) -> None:
    nowish = timezone.now() + timedelta(minutes=20)
    user = context.users[creator_role]["user"]

    release_calendar_page = ReleaseCalendarPageFactory(
        release_date=nowish, title="Release Calendar Page bundles UI", status=ReleaseStatus.CONFIRMED
    )
    mark_page_as_ready_to_publish(release_calendar_page, user)
    release_calendar_page.save_revision().publish()
    context.release_calendar_page = release_calendar_page


@given("there is a preview team")
def preview_teams_create(context: Context) -> None:
    context.team = Team.objects.create(identifier="preview-team", name="Bundles UI Preview team", is_active=True)


@given("the {user_role} is a member of the preview team")
def add_user_to_preview_teams(context: Context, user_role: str) -> None:
    user = context.users[user_role]["user"]
    user.teams.add(context.team)


@given("there are {number_of_bundles} bundles with {bundle_details}")
def multiple_bundles_create(context: Context, number_of_bundles: str, bundle_details: str) -> None:
    bundle_dets = json.loads(bundle_details)
    context.bundles = []
    context.bundlepages = []
    context.bundleteams = []

    for __ in range(int(number_of_bundles)):
        bundle = BundleFactory()
        bundle_status = BundleStatus.DRAFT
        bundle_approved = False
        if bundle_dets["status"] == "Approved":
            bundle_status = BundleStatus.APPROVED
            bundle_approved = True
        elif bundle_dets["status"] == "In_Review":
            bundle_status = BundleStatus.IN_REVIEW

        if bundle_dets["creator_role"] != "":
            user = context.users[bundle_dets["creator_role"]]["user"]

            bundle.created_by = user
            bundle.status = bundle_status
            bundle.approved = bundle_approved

        else:
            bundle.status = bundle_status
            bundle.approved = bundle_approved
        bundle.save()

        if bool(bundle_dets["preview_teams"]) and hasattr(context, "team"):
            BundleTeam.objects.create(parent=bundle, team=context.team)
            context.bundleteams.append({"parent": bundle, "team": context.team})
        bundle.save()

        if bool(bundle_dets["add_rel_cal"]) and hasattr(context, "release_calendar_page"):
            bundle.release_calendar_page = context.release_calendar_page
        else:
            now = (datetime.now() + timedelta(hours=4)).strftime("%Y-%m-%d %H:%M")
            bundle.publication_date = now
        bundle.save()

        if bool(bundle_dets["add_stat_page"]) and hasattr(context, "statistical_article_page"):
            page = context.statistical_article_page
            BundlePage.objects.create(parent=bundle, page=page)
        bundle.save()
        context.bundles.append(bundle)
        sorted(context.bundles, key=lambda x: x.name)


# Bundles UI Triggers
@step("the {user_role} logs in")
def log_in_user_by_role(context: Context, user_role: str) -> None:
    context.page.goto(f"{context.base_url}/admin/login/")
    context.page.get_by_placeholder("Enter your username").fill(context.users[user_role]["username"])
    context.page.get_by_placeholder("Enter password").fill(context.users[user_role]["password"])
    context.page.get_by_role("button", name="Sign in").click()


# Bundles UI Consequences
@step("the logged in user can see the create button")
def see_create_button(context: Context) -> None:
    expect(context.page.get_by_role("link", name="Add bundle")).to_be_visible()


@step("the logged in user can create a bundle")
def create_bundle(context: Context) -> None:
    context.page.get_by_role("link", name="Add bundle").click()


@step("the logged in user cannot see the create button")
def cannot_create_bundle(context: Context) -> None:
    expect(context.page.get_by_role("link", name="Add bundle")).not_to_be_visible()


@step("the {user_role} can find the bundle")
def find_the_bundle(context: Context, user_role: str) -> None:
    bundles_search_button = f"{context.bundles[-1].name} Edit Inspect"
    if user_role == "Viewer":
        bundles_search_button = f"{context.bundles[-1].name} Inspect"

    context.page.get_by_role("textbox", name="Search term").fill(context.bundles[-1].name)
    expect(context.page.get_by_text("There is 1 match")).to_be_visible()
    expect(context.page.get_by_role("table")).to_contain_text(bundles_search_button)


@step("the logged in user cannot find the bundle")
def not_find_the_bundle(context: Context) -> None:
    context.page.get_by_role("textbox", name="Search term").fill(context.bundles[-1].name)
    expect(context.page.get_by_text("No bundles match your query.")).to_be_visible()


@step("the logged in user goes to edit bundle")
def edit_bundle(context: Context) -> None:
    context.page.get_by_role("link", name=context.bundles[-1].name, exact=True).click()


@step("the logged in user can add a release schedule")
def add_release_calendar_in_edit(context: Context) -> None:
    # add Release Calendar
    bundle_status = f"Bundle '{context.bundles[-1].name}' updated."
    if hasattr(context, "release_calendar_pages"):
        context.page.get_by_role("button", name="Choose Release Calendar page").click()
        context.page.get_by_role("textbox", name="Search term").fill(context.release_calendar_page.title)
        context.page.get_by_role("row", name=context.release_calendar_page.title).get_by_role("link").click()
    else:
        now = (datetime.now() + timedelta(hours=4)).strftime("%Y-%m-%d %H:%M")
        context.page.get_by_role("textbox", name="or Publication date").fill(now)

    context.page.get_by_role("button", name="Save").click()
    expect(context.page.get_by_role("status")).to_contain_text(bundle_status)


@step("the logged in user can add preview team")
def add_preview_team_in_edit(context: Context) -> None:
    # add preview team
    context.page.get_by_role("button", name="Add preview team").click()
    context.page.get_by_role("textbox", name="Search term").fill(context.team.name)
    context.page.get_by_role("checkbox", name=context.team.name).check()
    context.page.get_by_role("button", name="Confirm selection").click()
    context.page.get_by_role("button", name="Save").click()


@step("the logged in user can add pages")
def add_article_page_in_edit(context: Context) -> None:
    # add Article
    bundle_status = f"Bundle '{context.bundles[-1].name}' updated."
    context.page.get_by_role("button", name="Add page").click()
    context.page.get_by_label("Page type").select_option("StatisticalArticlePage")
    context.page.wait_for_timeout(200)
    context.page.get_by_role(
        "checkbox", name=f"{context.article_series_page.title}: {context.statistical_article_page.title}"
    ).check()
    context.page.wait_for_timeout(100)
    context.page.get_by_role("button", name="Confirm selection").click()
    context.page.get_by_role("button", name="Save").click()
    expect(context.page.get_by_role("status")).to_contain_text(bundle_status)


@step("the {user_role} can preview bundle")
def goes_to_preview_bundle(context: Context, user_role: str) -> None:
    bundle_inspect_button = f"Inspect '{context.bundles[-1].name}'"
    context.page.get_by_role("link", name=bundle_inspect_button).click()

    # Verify required bundle
    expect(context.page.get_by_text("Name")).to_be_visible()
    expect(context.page.get_by_role("definition").filter(has_text=context.bundles[-1].name)).to_be_visible()

    if user_role != "Viewer":
        expect(context.page.get_by_role("term").filter(has_text=re.compile(r"^Status$"))).to_be_visible()
        expect(context.page.get_by_text("Approval status")).to_be_visible()
        expect(context.page.get_by_text("Pending approval")).to_be_visible()
        expect(context.page.get_by_text("Teams", exact=True)).to_be_visible()
        expect(context.page.get_by_text(context.team.name)).to_be_visible()

    expect(context.page.get_by_text("Created at")).to_be_visible()
    expect(context.page.get_by_text("Created by")).to_be_visible()
    expect(context.page.get_by_text("Scheduled publication")).to_be_visible()
    expect(context.page.get_by_text("Associated release calendar")).to_be_visible()
    expect(context.page.get_by_text("Datasets", exact=True)).to_be_visible()


@step("the logged in user cannot approve a bundle")
def cannot_preview_bundle(context: Context) -> None:
    context.page.get_by_role("link", name="Edit").click()
    context.page.get_by_role("button", name="More actions").click()
    context.page.get_by_role("button", name="Approve").click()
    expect(context.page.get_by_role("status")).to_contain_text(
        "The bundle could not be saved due to errors. Cannot approve the bundle without any pages or datasets"
    )


@step("the logged in user can approve a bundle")
def can_approve_bundle(context: Context) -> None:
    bundle_button = f"Edit '{context.bundles[-1].name}'"
    context.page.get_by_role("link", name=bundle_button).click()
    context.page.get_by_role("button", name="More actions").click()
    context.page.get_by_role("button", name="Approve").click()
    expect(context.page.get_by_text("Ready to publish").first).to_be_visible()


@step("the logged in user cannot approve a bundle due to lack of pages")
def cannot_approve_bundle_edge_case(context: Context) -> None:
    bundle_button = f"Edit '{context.bundles[-1].name}'"
    context.page.get_by_role("link", name=bundle_button).click()
    context.page.get_by_role("button", name="More actions").click()
    context.page.get_by_role("button", name="Approve").click()
    expect(context.page.get_by_role("status")).to_contain_text(
        "The bundle could not be saved due to errors. Cannot approve the bundle without any pages or datasets"
    )


@step("the logged in user gets a success message")
def success_message(context: Context) -> None:
    expect(context.page.get_by_role("status")).to_contain_text("Bundle successfully created.")
    expect(context.page.get_by_text("Bundle successfully created.")).to_be_visible()


@step("the logged in user gets a failure message due to field validation")
def fail_to_save_bundle_name(context: Context) -> None:
    expect(context.page.get_by_role("status")).to_contain_text("The bundle could not be created due to errors.")
    expect(context.page.locator("#panel-child-name-errors")).to_contain_text("This field is required.")


@step("the logged in user gets a failure message due to duplicate name")
def existing_failure_message(context: Context) -> None:
    expect(context.page.get_by_role("status")).to_contain_text("The bundle could not be created due to errors.")
    expect(context.page.locator("#panel-child-name-errors")).to_contain_text("Bundle with this Name already exists.")


@step("the logged in user gets a failure message due to duplicate schedule")
def schedule_failure_message(context: Context) -> None:
    expect(context.page.locator("#panel-child-scheduling-child-release_calendar_page-errors")).to_contain_text(
        "You must choose either a Release Calendar page or a Publication date, not both."
    )
    expect(context.page.get_by_role("status")).to_contain_text("The bundle could not be created due to errors.")
    expect(context.page.locator("#panel-child-scheduling-child-publication_date-errors")).to_contain_text(
        "You must choose either a Release Calendar page or a Publication date, not both."
    )


@step("the logged in user sends the bundle to preview")
def send_bundle_to_moderation(context: Context) -> None:
    context.page.get_by_role("button", name="More actions").click()
    context.page.get_by_role("button", name="Save to preview").click()


@step("the logged in user gets a bundle update message")
def update_message(context: Context) -> None:
    bundle_status = f"Bundle '{context.bundles[-1].name}'"
    expect(context.page.get_by_text(bundle_status)).to_be_visible()


@step("the logged in user adds a Name to the bundle")
def add_name_to_bundle(context: Context) -> None:
    bundle_name = "Bundle UI Test Bundle"
    if "bundles" in context:
        bundle_name = context.bundles[-1].name
    context.page.get_by_role("textbox", name="Name*").fill(bundle_name)


@step("the logged in user adds a Release Calendar page to the bundle")
def add_release_calendar_to_bundle(context: Context) -> None:
    context.page.get_by_role("button", name="Choose Release Calendar page").click()
    context.page.get_by_role("textbox", name="Search term").fill(context.release_calendar_page.title)
    context.page.get_by_role("row", name=context.release_calendar_page.title).get_by_role("link").click()


@step("the logged in user add a schedule date to the bundle")
def add_schedule_date(context: Context) -> None:
    now = (datetime.now() + timedelta(hours=4)).strftime("%Y-%m-%d %H:%M")
    context.page.get_by_role("textbox", name="or Publication date").fill(now)


@step("the logged in user goes to the bundle page")
def go_to_bundle_page(context: Context) -> None:
    context.page.get_by_role("link", name="Bundles", exact=True).click()


@step("the logged in user tries to find a non existing release calendar page")
def find_release_calendar(context: Context) -> None:
    release_calendar_name = "PFM December 2025"
    context.page.get_by_role("button", name="Choose Release Calendar page").click()
    context.page.get_by_role("textbox", name="Search term").fill(release_calendar_name)


@step("the logged in user gets the following message for {search_type}")
def search_alert(context: Context, search_type: str) -> None:
    search_name = "December 2025"
    if search_type == "release_calendar":
        search_name = "PFM December 2025"
    alert_text = f"Sorry, there are no matches for \"{search_name}\""
    expect(context.page.get_by_role("alert")).to_contain_text(alert_text)

@step("the logged in user tries to find a non existing bundle page")
def find_bundle_page(context: Context) -> None:
    bundle_page_name = "December 2025"
    context.page.get_by_role("button", name="Add page").click()
    context.page.get_by_role("textbox", name="Search term").fill(bundle_page_name)
