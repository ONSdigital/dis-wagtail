import os
from pathlib import Path

import django
from behave import use_fixture
from behave.model import Scenario
from behave.model_core import Status
from behave.runner import Context
from django.test.utils import override_settings
from playwright.sync_api import sync_playwright

from functional_tests.behave_fixtures import django_test_case, django_test_runner
from functional_tests.step_helpers.utils import str_to_bool

# Ensure the correct Django settings module is used
os.environ["DJANGO_SETTINGS_MODULE"] = "cms.settings.functional_test"

# This setting is required for Django to run within a Poetry shell
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "True"

# The factory classes require Django to have been set up at their import time.
# To ensure Django set up happens before that point, we call setup at the module level here.
# This will get called again during the test runner setup in the before_all hook,
# but that happens too late to solve import time issues.
django.setup()


# Imported after django.setup() as auth_utils import Django models and requires Django to be initialised.
from functional_tests.step_helpers.auth_utils import (  # noqa: E402 # pylint: disable=wrong-import-position
    capture_request,
    get_cognito_overridden_settings,
)
from functional_tests.step_helpers.bundles_api import (  # noqa: E402 # pylint: disable=wrong-import-position
    mock_bundle_api,
    prepare_dataset_content_item,
)
from functional_tests.step_helpers.datasets import (  # noqa: E402 # pylint: disable=wrong-import-position
    TEST_UNPUBLISHED_DATASETS,
)


def before_all(context: Context) -> None:
    """Runs once before all tests.
    Sets up playwright browser and context to be used in all scenarios.
    """
    # Register our django test runner so the entire test run is wrapped in a django test runner
    use_fixture(django_test_runner, context=context)

    context.playwright = sync_playwright().start()
    context.playwright_trace = str_to_bool(os.getenv("PLAYWRIGHT_TRACE", "True"))
    context.playwright_traces_dir = Path(os.getenv("PLAYWRIGHT_TRACES_DIR", str(Path.cwd().joinpath("tmp_traces"))))

    configure_and_launch_playwright_browser(context)

    if context.playwright_trace:
        context.playwright_traces_dir.mkdir(exist_ok=True)
        # Start the main trace for both browser contexts, we will record individual scenario traces in chunks
        context.browser_context.tracing.start(screenshots=True, snapshots=True, sources=True)
        context.no_javascript_context.tracing.start(
            screenshots=True,
            snapshots=True,
            sources=True,
            title="JavaScript disabled",
        )


def configure_and_launch_playwright_browser(context: Context, slow_mo: int = 0) -> None:
    """Configures and launches a playwright browser and browser context for use in the tests."""
    browser_type = os.getenv("PLAYWRIGHT_BROWSER", "chromium")
    headless = str_to_bool(os.getenv("PLAYWRIGHT_HEADLESS", "True"))
    slow_mo = int(os.getenv("PLAYWRIGHT_SLOW_MO", slow_mo))
    default_browser_timeout = int(os.getenv("PLAYWRIGHT_DEFAULT_BROWSER_TIMEOUT", "5_000"))

    browser_kwargs = {
        "headless": headless,
        "slow_mo": slow_mo,
    }

    match browser_type:
        case "chromium":
            context.browser = context.playwright.chromium.launch(**browser_kwargs)
        case "firefox":
            context.browser = context.playwright.firefox.launch(**browser_kwargs)
        case "webkit":
            context.browser = context.playwright.webkit.launch(**browser_kwargs)
        case _:
            raise ValueError(f'Unknown browser set: {browser_type}, must be one of ["chromium", "firefox", "webkit"]')

    context.browser_context = context.browser.new_context()
    context.browser_context.set_default_timeout(default_browser_timeout)

    context.no_javascript_context = context.browser.new_context(
        java_script_enabled=False,
    )


def after_all(context: Context) -> None:
    """Runs once after all tests.
    Cleans up playwright objects.
    """
    if context.playwright_trace:
        context.browser_context.tracing.stop()
        context.no_javascript_context.tracing.stop()

    context.browser_context.close()
    context.no_javascript_context.close()
    context.browser.close()
    context.playwright.stop()


def before_scenario(context: Context, scenario: Scenario) -> None:
    """Runs before each scenario.
    Create a new playwright page to be used by the scenario, passed through the behave context.
    """
    # Register our django test case fixture so every scenario is wrapped in a Django test case
    use_fixture(django_test_case, context=context)

    if "no_javascript" in scenario.tags:
        # If the scenario is tagged with no_javascript, use the no_javascript_context
        context.playwright_context = context.no_javascript_context
    else:
        # Otherwise use the default context
        context.playwright_context = context.browser_context

    # Only set up request capture and mocking for scenarios tagged with 'cognito_enabled'
    if "cognito_enabled" in scenario.tags or "cognito_enabled" in getattr(scenario.feature, "tags", []):
        context._requests = []  # pylint: disable=protected-access
        context.playwright_context.route("**/*", capture_request(context))

    if "slow_mo" in scenario.tags and "PLAYWRIGHT_SLOW_MO" not in os.environ:
        # replace the original browser with a slow-motion verion
        context.browser.close()
        configure_and_launch_playwright_browser(context, slow_mo=200)

    context.page = context.playwright_context.new_page()

    # For debugging purposes, log all console messages from the page;
    # this can be useful to see errors from the dis-authorisation-client-js library
    context.page.on("console", lambda msg: print(f"[PAGE][{msg.type}] {msg.text}"))

    if context.playwright_trace:
        # Start a new tracing chunk to capture each scenario separately
        context.playwright_context.tracing.start_chunk(name=scenario.name, title=scenario.name)


def after_scenario(context: Context, scenario: Scenario) -> None:
    """Runs after each scenario.
    Write out a Playwright trace if the scenario failed and trace recording is enabled, then close the playwright page.
    """
    if context.playwright_context and scenario.status == Status.failed:
        # If the scenario failed, write the trace chunk out to a file, which will be prefixed with the scenario name
        context.playwright_context.tracing.stop_chunk(
            path=context.playwright_traces_dir.joinpath(f"{scenario.name.replace(' ', '_')}_failure_trace.zip")
        )

    elif context.playwright_trace:
        # Else end the trace chunk without saving to a file
        context.playwright_context.tracing.stop_chunk()

    if "slow_mo" in scenario.tags and "PLAYWRIGHT_SLOW_MO" not in os.environ:
        # reset the browser
        context.browser.close()
        configure_and_launch_playwright_browser(context)

    context.page.close()


def before_tag(context: Context, tag: str) -> None:
    """Handle tag-specific setup."""
    if tag == "cognito_enabled":
        # Apply Cognito test settings
        settings = get_cognito_overridden_settings()
        context.aws_override = override_settings(**settings)
        context.aws_override.enable()
    elif tag == "bundle_api_enabled":
        # Enable Bundle API integration for this scenario
        context.bundle_api_override = override_settings(DIS_DATASETS_BUNDLE_API_ENABLED=True)
        context.bundle_api_override.enable()

        # Create Bundle API content items from TEST_UNPUBLISHED_DATASETS
        contents = []
        for idx, dataset in enumerate(TEST_UNPUBLISHED_DATASETS, start=1):
            contents.append(
                prepare_dataset_content_item(
                    content_id=f"content-{idx}",  # We use start=1 to avoid content-0
                    dataset_id=dataset["dataset_id"],
                    edition_id=dataset["edition"],
                    version_id=int(dataset["latest_version"]["id"]),
                    title=dataset["title"],
                    state="APPROVED",
                )
            )

        # Set up Bundle API mocks for the scenario
        context.bundle_api_cm = mock_bundle_api(contents=contents)
        # Enter the Bundle API mock context manager - we have to do the dunder call manually here
        # because our steps run within the scenario
        context.bundle_api_cm.__enter__()  # pylint: disable=unnecessary-dunder-call


def after_tag(context: Context, tag: str) -> None:
    """Handle tag-specific cleanup."""
    if tag == "cognito_enabled":
        # Disable settings override
        context.aws_override.disable()
    elif tag == "bundle_api_enabled":
        # Disable Bundle API settings override
        context.bundle_api_override.disable()

        # Exit the Bundle API mock context manager
        context.bundle_api_cm.__exit__(None, None, None)
