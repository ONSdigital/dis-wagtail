from behave import given, step, then, when  # pylint: disable=no-name-in-module
from behave.runner import Context
from django.conf import settings
from playwright.sync_api import expect

from cms.settings.base import ONS_ALLOWED_LINK_DOMAINS
from functional_tests.step_helpers.datasets import (
    TEST_MIXED_STATES_DATASETS,
    TEST_UNPUBLISHED_DATASETS,
    mock_datasets_responses,
)


@given("the user is in an internal environment")
def user_in_internal_environment(context: Context) -> None:
    context.is_internal_environment = True


@when("looks up and selects a dataset")
def look_up_and_select_published_dataset(context: Context) -> None:
    mock_dataset, unpublished_mock_dataset = TEST_MIXED_STATES_DATASETS
    dataset_displayed_fields = {
        "title": mock_dataset["title"],
        "description": mock_dataset["description"],
        "url": f"{settings.ONS_WEBSITE_BASE_URL}/datasets/{mock_dataset['dataset_id']}",
    }

    context.selected_datasets = [
        *getattr(context, "selected_datasets", []),
        dataset_displayed_fields,
    ]

    editor_tab = getattr(context, "editor_tab", "content")

    # Mock dataset API responses
    is_internal_environment = getattr(context, "is_internal_environment", False)
    with mock_datasets_responses([mock_dataset, unpublished_mock_dataset], use_old_schema=is_internal_environment):
        context.page.locator(get_datasets_panel_locator(editor_tab)).get_by_role(
            "button", name="Insert a block"
        ).first.click()
        context.page.get_by_text("Lookup Dataset").click()
        context.page.get_by_role("button", name="Choose a dataset").click()
        context.page.get_by_role("link", name=mock_dataset["title"]).click()
        context.page.wait_for_timeout(500)


@when("the user opens the dataset chooser")
def open_dataset_chooser(context: Context) -> None:
    mock_dataset, unpublished_mock_dataset = TEST_MIXED_STATES_DATASETS

    editor_tab = getattr(context, "editor_tab", "content")

    with mock_datasets_responses([mock_dataset, unpublished_mock_dataset]):
        context.page.locator(get_datasets_panel_locator(editor_tab)).get_by_role(
            "button", name="Insert a block"
        ).first.click()
        context.page.get_by_text("Lookup Dataset").click()
        context.page.get_by_role("button", name="Choose a dataset").click()
        context.page.wait_for_timeout(500)  # Wait for modal to open and the events to settle


@when("the user opens the dataset chooser and sets the filter to published datasets")
def set_filter_to_published_datasets(context: Context) -> None:
    mock_dataset, unpublished_mock_dataset = TEST_MIXED_STATES_DATASETS

    editor_tab = getattr(context, "editor_tab", "content")

    with mock_datasets_responses([mock_dataset, unpublished_mock_dataset]):
        context.page.locator(get_datasets_panel_locator(editor_tab)).get_by_role(
            "button", name="Insert a block"
        ).first.click()
        context.page.get_by_text("Lookup Dataset").click()
        context.page.get_by_role("button", name="Choose a dataset").click()
        context.page.wait_for_timeout(500)  # Wait for modal to open and the events to settle
        context.page.get_by_label("Published status").select_option("true")
        context.page.wait_for_timeout(500)  # Wait for filter to apply


@when("manually enters a dataset link")
def manually_enter_dataset_link(context: Context) -> None:
    editor_tab = getattr(context, "editor_tab", "content")
    context.page.locator(get_datasets_panel_locator(editor_tab)).get_by_role(
        "button", name="Insert a block"
    ).first.click()
    manual_dataset = {
        "title": "Manual Dataset",
        "description": "Manually entered test dataset",
        "url": f"https://{ONS_ALLOWED_LINK_DOMAINS[0]}/manual-dataset",
    }
    context.selected_datasets = [
        *getattr(context, "selected_datasets", []),
        manual_dataset,
    ]
    context.page.get_by_role("option", name="Manually Linked Dataset").click()
    context.page.get_by_role("region", name="Datasets").get_by_label("Title*").fill(manual_dataset["title"])
    context.page.get_by_role("region", name="Datasets").get_by_label("Description").fill(manual_dataset["description"])
    context.page.get_by_role("region", name="Datasets").get_by_label("Url*").fill(manual_dataset["url"])


@step("the user selects multiple datasets")
def the_user_selects_multiple_datasets(context: Context) -> None:
    mock_dataset_a, mock_dataset_b, mock_dataset_c = TEST_UNPUBLISHED_DATASETS

    is_internal_environment = getattr(context, "is_internal_environment", False)

    # Mock dataset API responses
    with mock_datasets_responses(
        [mock_dataset_a, mock_dataset_b, mock_dataset_c], use_old_schema=is_internal_environment
    ):
        context.page.get_by_role("button", name="Add dataset").click()
        context.page.wait_for_timeout(500)  # Wait for modal to open and the events to settle
        context.page.get_by_role("checkbox", name="Looked up dataset").click()
        context.page.get_by_role("checkbox", name="Personal well-being estimates by local authority").click()
        context.page.get_by_role("checkbox", name="Deaths registered weekly in England and Wales by region").click()
        context.page.get_by_role("button", name="Confirm selection").click()
        context.page.wait_for_timeout(250)  # Wait for everything to process before leaving the with block


@when("the user opens the bundle datasets chooser")
def user_opens_bundle_datasets_chooser(context: Context) -> None:
    mock_dataset = TEST_MIXED_STATES_DATASETS[0]

    with mock_datasets_responses([mock_dataset]):
        context.page.get_by_role("button", name="Add dataset").click()
        context.page.wait_for_timeout(500)  # Wait for modal to open and the events to settle


def get_datasets_panel_locator(editor_tab: str = "content") -> str:
    return f"#panel-child-{editor_tab}-datasets-content"


@then("the selected datasets are displayed on the page")
@then("the selected dataset is displayed on the page")
def check_selected_datasets_are_displayed(context: Context) -> None:
    expect(context.page.get_by_role("heading", name="Data", exact=True)).to_be_visible()

    for dataset in context.selected_datasets:
        expect(context.page.get_by_role("link", name=dataset["title"])).to_be_visible()
        expect(context.page.get_by_text(dataset["description"])).to_be_visible()


@then("unpublished datasets are shown by default in the dataset chooser")
def check_unpublished_datasets_shown_by_default(context: Context) -> None:
    expect(context.page.get_by_role("link", name="Unpublished Looked Up Dataset")).to_be_visible()
    expect(context.page.get_by_role("link", name="Looked Up Dataset", exact=True)).not_to_be_visible()


@then("only published datasets are shown in the dataset chooser")
def check_only_published_datasets_shown(context: Context) -> None:
    expect(context.page.get_by_role("link", name="Looked Up Dataset", exact=True)).to_be_visible()
    expect(context.page.get_by_role("link", name="Unpublished Looked Up Dataset")).not_to_be_visible()


@then("the published state filter is not displayed in the chooser")
def check_published_state_filter_not_displayed(context: Context) -> None:
    expect(context.page.get_by_label("Published status")).not_to_be_visible()
