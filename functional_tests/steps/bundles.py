import json
from datetime import timedelta

from behave import given, step, then, when  # pylint: disable=no-name-in-module
from behave.runner import Context
from django.urls import reverse
from django.utils import timezone
from playwright.sync_api import expect

from cms.articles.tests.factories import ArticleSeriesPageFactory, StatisticalArticlePageFactory
from cms.bundles.enums import BundleStatus
from cms.bundles.models import BundlePage, BundleTeam
from cms.bundles.tests.factories import BundleFactory
from cms.release_calendar.enums import ReleaseStatus
from cms.release_calendar.tests.factories import ReleaseCalendarPageFactory
from cms.teams.models import Team
from cms.users.tests.factories import UserFactory
from cms.workflows.tests.utils import mark_page_as_ready_to_publish
from functional_tests.step_helpers.users import create_user


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
def bundle_menu_contains_value(context: Context) -> None:
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


# Bundles UI Data Setup


@given("there is a {user_role} user")
def a_user_exists_by_role(context: Context, user_role: str) -> None:
    if not hasattr(context, "users"):
        context.users = []

    context.users.append({user_role: create_user(user_role)})


@given("there are {no_statistical_analysis} Statistical Analysis pages")
def multiple_statistical_analysis(context: Context, no_statistical_analysis: str) -> None:
    context.statistical_article_pages = []
    if no_statistical_analysis.isdigit():
        for statistical_analysis_index in range(int(no_statistical_analysis)):
            article = StatisticalArticlePageFactory(
                parent=ArticleSeriesPageFactory(title="PSF" + str(statistical_analysis_index))
            )
            mark_page_as_ready_to_publish(article, UserFactory())
            context.statistical_article_pages.append(article)


@given("there are {no_release_calendar} release calendar pages")
def multiple_release_calendar(context: Context, no_release_calendar: str) -> None:
    context.release_calendar_pages = []
    if no_release_calendar.isdigit():
        for release_calendar_index in range(int(no_release_calendar)):
            nowish = timezone.now() + timedelta(minutes=5 * (release_calendar_index + 1))
            context.release_calendar_pages.append(
                ReleaseCalendarPageFactory(
                    release_date=nowish,
                    title="Release Calendar Page" + str(release_calendar_index),
                    status=ReleaseStatus.CONFIRMED,
                )
            )


@given("there are {no_preview_teams} Preview teams")
def multiple_preview_teams_create(context: Context, no_preview_teams: str) -> None:
    context.teams = []
    if no_preview_teams.isdigit():
        for preview_team_index in range(int(no_preview_teams)):
            context.teams.append(
                Team.objects.create(
                    identifier="preview-team-" + str(preview_team_index), name="Preview_Team_" + str(preview_team_index)
                )
            )


@given("the {user_role} is a member of the Preview teams")
def add_user_to_preview_teams(context: Context, user_role: str) -> None:
    next((item[user_role]["user"] for item in context.users if item[user_role]), None).teams.add(*context.teams)


@given("there are {number_of_bundles} bundles with {bundle_details}")
def multiple_bundles_create(context: Context, number_of_bundles: str, bundle_details: str) -> None:
    bundle_dets = {}
    if json_str_to_dict(bundle_details):
        bundle_dets = json.loads(bundle_details)

    context.bundles = []

    if number_of_bundles.isdigit():
        for __ in range(int(number_of_bundles)):
            if not next(item for item in context.users if bundle_dets["Creator Role"] in item):
                context.users.append({bundle_dets["Creator Role"]: create_user(bundle_dets["Creator Role"])})

            bundle_creator = next(item for item in context.users if bundle_dets["Creator Role"] in item)
            bundle_status = BundleStatus.DRAFT
            bundle_approved = False
            if bundle_dets["status"] == "Approved":
                bundle_status = BundleStatus.APPROVED
                bundle_approved = True
            if bundle_dets["status"] == "In_Review":
                bundle_status = BundleStatus.IN_REVIEW
            bundle = BundleFactory(
                created_by=bundle_creator.get("user"),
                status=bundle_status,
                approved=bundle_approved,
            )
            context.bundles.append(bundle)

            if bool(bundle_dets["preview_teams"]) and hasattr(context, "teams"):
                add_teams(context)

            if bool(bundle_dets["add_rel_cal"]) and hasattr(context, "release_calendar_pages"):
                add_release_calendar(context)

            if bool(bundle_dets["add_stat_page"]) and hasattr(context, "statistical_article_pages"):
                add_article_pages(context)


def add_article_pages(context: Context) -> None:
    for page in context.statistical_article_pages:
        for bundle in context.bundles:
            BundlePage.objects.create(parent=bundle, page=page)


def add_release_calendar(context: Context):
    for page in context.release_calendar_pages:
        for bundle in context.bundles:
            BundlePage.objects.create(parent=bundle, page=page)


def add_teams(context: Context) -> None:
    for team in context.teams:
        for bundle in context.bundles:
            BundleTeam.objects.create(parent=bundle, team=team)


def json_str_to_dict(bundle_details):
    try:
        return json.loads(bundle_details)
    except ValueError as e:
        print(e)
        return False


# Bundles UI Triggers
@when("the {user_role} logs in")
def log_in_user_by_role(context: Context, user_role: str) -> None:
    context.page.goto(f"{context.base_url}/admin/login/")
    context.page.get_by_placeholder("Enter your username").fill(
        next(d.get(user_role)["username"] for d in context.users)
    )
    context.page.get_by_placeholder("Enter password").fill(next(d.get(user_role)["password"] for d in context.users))
    context.page.get_by_role("button", name="Sign in").click()


# Bundles UI Consequences
@then("the user can create a bundle")
def add_bundle_details(context: Context) -> None:
    bundle_name = "Bundle UI Test 1"
    expect(context.page.locator("#latest-bundles-content")).to_contain_text("Add bundle")
    context.page.get_by_role("link", name="Add bundle").click()
    context.page.get_by_role("textbox", name="Name*").click()
    context.page.get_by_role("textbox", name="Name*").fill(bundle_name)
    context.page.get_by_role("button", name="Save as draft").click()
    context.page.get_by_role("link", name="Dashboard").click()
    expect(context.page.get_by_text("Latest active bundles")).to_be_visible()
    expect(context.page.get_by_role("link", name=bundle_name)).to_be_visible()


@then("the user cannot create a bundle")
def the_user_cannot_add_bundles(context: Context) -> None:
    expect(context.page.get_by_role("link", name="Add bundle")).not_to_be_visible()
    expect(context.page.get_by_text("Bundles ready for preview")).to_be_visible()
    expect(context.page.get_by_text("There are currently no")).to_be_visible()


@step("the {user_role} can edit a bundle")
def can_edit_bundle(context: Context) -> None:
    expect(context.page.locator("#latest-bundles-heading")).to_contain_text("Latest active bundles")
    expect(context.page.locator("#latest-bundles-content")).to_contain_text(context.bundles[0].name)
    context.page.get_by_role("row", name=context.bundles[0].name + " Actions").get_by_label("Actions").click()
    context.page.get_by_role("link", name="Edit", exact=True).click()

    add_reslease_calendar_in_edit(context)
    context.page.get_by_role("button", name="Save").click()
    add_article_page_in_edit(context)
    context.page.get_by_role("button", name="Save").click()
    add_preview_team_in_edit(context)
    context.page.get_by_role("button", name="Save").click()

    context.page.get_by_role("button", name="More actions").click()
    context.page.get_by_role("button", name="Save to preview").click()


def add_preview_team_in_edit(context: Context) -> None:
    # add preview team
    if hasattr(context, "teams"):
        expect(context.page.locator("#panel-preview_teams-heading")).to_contain_text("Preview teams")
        context.page.get_by_role("button", name="Add preview team").click()
        expect(context.page.get_by_role("textbox", name="Search term")).to_be_visible()
        context.page.get_by_role("textbox", name="Search term").click()
        context.page.get_by_role("textbox", name="Search term").fill(context.teams[0].name)
        expect(context.page.get_by_role("checkbox", name=context.teams[0].name)).to_be_visible()
        context.page.get_by_role("checkbox", name=context.teams[0].name).check()

        # expect(context.page.get_by_role("button", name="Confirm selection")).to_be_visible()
        # expect(context.page.locator("input[type=\"submit\"]")).to_contain_text("Confirm selection")
        # context.page.get_by_role("button", name="Confirm selection").click()

        expect(context.page.get_by_role("button", name="Confirm selection")).to_be_visible()
        context.page.get_by_role("button", name="Confirm selection").click()


def add_article_page_in_edit(context: Context) -> None:
    # add Article
    if hasattr(context, "statistical_article_pages"):
        expect(context.page.get_by_role("heading", name="Bundled pages").locator("span")).to_be_visible()
        expect(context.page.get_by_role("button", name="Add page")).to_be_visible()
        context.page.get_by_role("button", name="Add page").click()
        expect(context.page.get_by_role("heading", name="Choose a page")).to_be_visible()
        expect(context.page.get_by_text("Page type", exact=True)).to_be_visible()
        expect(context.page.get_by_label("Page type")).to_be_visible()
        context.page.get_by_label("Page type").select_option("StatisticalArticlePage")
        expect(context.page.get_by_text(context.statistical_article_pages[0].title)).to_be_visible()
        context.page.get_by_role("checkbox", name=context.statistical_article_pages[0].title).check()
        expect(context.page.get_by_role("button", name="Confirm selection")).to_be_visible()
        context.page.get_by_role("button", name="Confirm selection").click()


def add_reslease_calendar_in_edit(context: Context) -> None:
    # add Release Calendar
    if hasattr(context, "search_release_calendar"):
        expect(context.page.get_by_role("button", name="Choose Release Calendar page")).to_be_visible()
        context.page.get_by_role("button", name="Choose Release Calendar page").click()
        context.page.get_by_role("textbox", name="Search term").click()
        context.page.get_by_role("textbox", name="Search term").fill(context.release_calendar_pages[0].title)
        expect(context.page.get_by_role("link", name=context.release_calendar_pages[0].title)).to_be_visible()
        context.page.get_by_role("row", name=context.release_calendar_pages[0].title).get_by_role("link").click()
        context.page.get_by_role("link", name=context.release_calendar_pages[0].title).click()


@step("the {user_role} can preview a bundle")
def can_preview_bundle(context: Context, user_role: str) -> None:
    if user_role == "Viewer":
        expect(context.page.get_by_text("Bundles ready for preview")).to_be_visible()
        expect(context.page.get_by_role("link", name=context.bundles[0].name)).to_be_visible()
        context.page.get_by_role("link", name=context.bundles[0].name).click()

    else:
        expect(context.page.get_by_text("Latest active bundles")).to_be_visible()
        expect(context.page.get_by_role("link", name=context.bundles[0].name)).to_be_visible()
        expect(context.page.get_by_role("cell", name="In Preview")).to_be_visible()
        expect(
            context.page.get_by_role("row", name=context.bundles[0].name + " Actions").get_by_label("Actions")
        ).to_be_visible()
        (context.page.get_by_role("row", name=context.bundles[0].name + " Actions").get_by_label("Actions").click())
        context.page.get_by_role("link", name="View", exact=True).click()

    expect(context.page.locator("header")).to_contain_text(context.bundles[0].name)
    expect(context.page.get_by_text("Name")).to_be_visible()
    expect(context.page.get_by_text(context.bundles[0].name).nth(2)).to_be_visible()
    expect(context.page.get_by_text("Created at")).to_be_visible()
    expect(context.page.get_by_text("Created by")).to_be_visible()
    expect(context.page.get_by_text("Associated release calendar")).to_be_visible()
    expect(context.page.get_by_text("Pages")).to_be_visible()
    expect(context.page.get_by_text("Datasets", exact=True)).to_be_visible()
    expect(context.page.get_by_text("No datasets in bundle")).to_be_visible()
    context.page.get_by_role("link", name="Preview").click()
    expect(context.page.get_by_role("heading", name="Statistical article")).to_be_visible()


@step("the {user_role} cannot preview a bundle")
def cannot_preview_bundle(context: Context) -> None:
    context.page.get_by_role("link", name="Bundles", exact=True).click()
    expect(context.page.get_by_role("button", name=f"More options for '{context.bundles[0].name}'")).not_to_be_visible()


@step("the {user_role} cannot approve a bundle")
def cannot_approve_bundle(context: Context) -> None:
    context.page.get_by_role("link", name="Bundles", exact=True).click()
    expect(context.page.get_by_role("button", name=f"More options for '{context.bundles[0].name}'")).not_to_be_visible()


@step("the {user_role} can approve a bundle")
def can_approve_bundle(context: Context) -> None:
    expect(context.page.get_by_text("Latest active bundles")).to_be_visible()
    expect(context.page.get_by_role("link", name=context.bundles[0].name)).to_be_visible()
    expect(context.page.get_by_role("cell", name="In Preview")).to_be_visible()
    expect(
        context.page.get_by_role("row", name=context.bundles[0].name + " Actions").get_by_label("Actions")
    ).to_be_visible()
    context.page.get_by_role("row", name=context.bundles[0].name + " Actions").get_by_label("Actions").click()
    context.page.get_by_role("link", name="Edit", exact=True).click()
    context.page.locator("#id_status").select_option("APPROVED")
    context.page.get_by_role("button", name="Save").click()


def create_user_by_role(context, user_role):
    context.user_data = create_user(user_role)
    if not next((item for item in context.users if item[user_role]), False):
        context.users.append({user_role: context.user_data})
