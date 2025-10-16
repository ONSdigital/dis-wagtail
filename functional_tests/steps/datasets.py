from behave import step, then, when  # pylint: disable=no-name-in-module
from behave.runner import Context
from django.conf import settings
from playwright.sync_api import expect

from cms.settings.base import ONS_ALLOWED_LINK_DOMAINS
from functional_tests.step_helpers.datasets import mock_datasets_responses


@when("looks up and selects a dataset")
def look_up_and_select_dataset(context: Context) -> None:
    mock_dataset = {
        "id": "example1",
        "dataset_id": "example1",
        "description": "Example dataset for functional testing",
        "title": "Looked Up Dataset",
        "version": "1",
        "edition": "example-dataset-1",
        "latest_version": {"id": "1"},
    }
    dataset_displayed_fields = {
        "title": mock_dataset["title"],
        "description": mock_dataset["description"],
        "url": f"{settings.ONS_WEBSITE_BASE_URL}/datasets/{mock_dataset['id']}",
    }

    context.selected_datasets = [
        *getattr(context, "selected_datasets", []),
        dataset_displayed_fields,
    ]

    editor_tab = getattr(context, "editor_tab", "content")

    # Mock dataset API responses
    with mock_datasets_responses([mock_dataset]):
        context.page.locator(get_datasets_panel_locator(editor_tab)).get_by_role(
            "button", name="Insert a block"
        ).first.click()
        context.page.get_by_text("Lookup Dataset").click()
        context.page.get_by_role("button", name="Choose a dataset").click()
        context.page.get_by_role("link", name=mock_dataset["title"]).click()
        context.page.wait_for_timeout(500)


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
    mock_dataset_a = {
        "id": "example1",
        "dataset_id": "example1",
        "description": "Example dataset for functional testing",
        "title": "Looked Up Dataset",
        "version": "1",
        "edition": "example-dataset-1",
        "latest_version": {"id": "1"},
    }

    mock_dataset_b = {
        "id": "example2",
        "dataset_id": "example2",
        "description": "Second example dataset for functional testing",
        "title": "Personal well-being estimates by local authority",
        "version": "1",
        "edition": "example-dataset-2",
        "latest_version": {"id": "1"},
    }

    mock_dataset_c = {
        "id": "example3",
        "dataset_id": "example3",
        "description": "Third example dataset for functional testing",
        "title": "Deaths registered weekly in England and Wales by region",
        "version": "1",
        "edition": "example-dataset-3",
        "latest_version": {"id": "1"},
    }

    # Mock dataset API responses
    with mock_datasets_responses([mock_dataset_a, mock_dataset_b, mock_dataset_c]):
        context.page.get_by_role("button", name="Add dataset").click()
        context.page.get_by_text("Looked up dataset").click()
        context.page.get_by_text("Personal well-being estimates by local authority").click()
        context.page.get_by_text("Deaths registered weekly in England and Wales by region").click()
        context.page.get_by_role("button", name="Confirm selection").click()


def get_datasets_panel_locator(editor_tab: str = "content") -> str:
    return f"#panel-child-{editor_tab}-datasets-content"


@then("the selected datasets are displayed on the page")
@then("the selected dataset is displayed on the page")
def check_selected_datasets_are_displayed(context: Context) -> None:
    expect(context.page.get_by_role("heading", name="Data", exact=True)).to_be_visible()

    for dataset in context.selected_datasets:
        expect(context.page.get_by_role("link", name=dataset["title"])).to_be_visible()
        expect(context.page.get_by_text(dataset["description"])).to_be_visible()
