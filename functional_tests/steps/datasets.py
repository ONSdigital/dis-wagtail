from behave import step, then, when  # pylint: disable=no-name-in-module
from behave.runner import Context
from django.conf import settings
from playwright.sync_api import expect

from cms.settings.base import ONS_ALLOWED_LINK_DOMAINS
from functional_tests.step_helpers.datasets import mock_datasets_responses


@when("looks up and selects a dataset")
def look_up_and_select_dataset(context: Context):
    mock_dataset = {
        "id": "example1",
        "description": "Example dataset for functional testing",
        "title": "Looked Up Dataset",
        "version": "1",
        "links": {
            "latest_version": {
                "href": "/datasets/example1/editions/example-dataset-1/versions/1",
                "id": "example1",
            },
        },
    }
    dataset_displayed_fields = {
        "title": mock_dataset["title"],
        "description": mock_dataset["description"],
        "url": settings.ONS_WEBSITE_DATASET_BASE_URL + mock_dataset["links"]["latest_version"]["href"],
    }

    context.selected_datasets = [*getattr(context, "selected_datasets", []), dataset_displayed_fields]

    with mock_datasets_responses(datasets=[mock_dataset]):
        editor_tab = getattr(context, "editor_tab", "content")
        context.page.locator(get_datasets_panel_locator(editor_tab)).get_by_role(
            "button", name="Insert a block"
        ).first.click()
        context.page.get_by_text("Lookup Dataset").click()
        context.page.get_by_role("button", name="Choose a dataset").click()
        context.page.get_by_role("link", name=mock_dataset["title"]).click()
        context.page.wait_for_timeout(500)


@when("manually enters a dataset link")
def manually_enter_dataset_link(context: Context):
    editor_tab = getattr(context, "editor_tab", "content")
    context.page.locator(get_datasets_panel_locator(editor_tab)).get_by_role(
        "button", name="Insert a block"
    ).first.click()
    manual_dataset = {
        "title": "Manual Dataset",
        "description": "Manually entered test dataset",
        "url": ONS_ALLOWED_LINK_DOMAINS[0] if ONS_ALLOWED_LINK_DOMAINS else "https://example.com",
    }
    context.selected_datasets = [*getattr(context, "selected_datasets", []), manual_dataset]
    context.page.get_by_role("option", name="Manually Linked Dataset").click()
    context.page.get_by_role("region", name="Datasets").get_by_label("Title*").fill(manual_dataset["title"])
    context.page.get_by_role("region", name="Datasets").get_by_label("Description").fill(manual_dataset["description"])
    context.page.get_by_role("region", name="Datasets").get_by_label("Url*").fill(manual_dataset["url"])


@step("the user selects multiple datasets")
def the_user_selects_multiple_datasets(context: Context) -> None:
    mock_dataset_a = {
        "id": "example1",
        "description": "Example dataset for functional testing",
        "title": "Looked Up Dataset",
        "version": "1",
        "links": {
            "latest_version": {
                "href": "/datasets/example1/editions/example-dataset-1/versions/1",
                "id": "example1",
            },
        },
    }

    mock_dataset_b = {
        "id": "example2",
        "description": "Second example dataset for functional testing",
        "title": "Personal well-being estimates by local authority",
        "version": "1",
        "links": {
            "latest_version": {
                "href": "/datasets/example2/editions/example-dataset-2/versions/1",
                "id": "example2",
            },
        },
    }

    mock_dataset_c = {
        "id": "example3",
        "description": "Third example dataset for functional testing",
        "title": "Deaths registered weekly in England and Wales by region",
        "version": "1",
        "links": {
            "latest_version": {
                "href": "/datasets/example3/editions/example-dataset-3/versions/1",
                "id": "example3",
            },
        },
    }

    with mock_datasets_responses(datasets=[mock_dataset_a, mock_dataset_b, mock_dataset_c]):
        context.page.get_by_role("button", name="Add dataset").click()
        context.page.get_by_text("Looked up dataset").click()
        context.page.get_by_text("Personal well-being estimates by local authority").click()
        context.page.get_by_text("Deaths registered weekly in England and Wales by region").click()
        context.page.get_by_role("button", name="Confirm selection").click()


def get_datasets_panel_locator(editor_tab: str = "content") -> str:
    return f"#panel-child-{editor_tab}-datasets-content"


@then("the selected datasets are displayed on the page")
@then("the selected dataset is displayed on the page")
def check_selected_datasets_are_displayed(context: Context):
    expect(context.page.get_by_role("heading", name="Data", exact=True)).to_be_visible()

    for dataset in context.selected_datasets:
        expect(context.page.get_by_role("link", name=dataset["title"])).to_be_visible()
        expect(context.page.get_by_text(dataset["description"])).to_be_visible()
