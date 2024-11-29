import os
from pathlib import Path

import django
from behave import use_fixture
from behave.model import Scenario
from behave.model_core import Status
from behave.runner import Context
from playwright.sync_api import BrowserContext, Page, Playwright, sync_playwright

from functional_tests.behave_fixtures import django_test_case, django_test_runner
from functional_tests.step_helpers.utilities import str_to_bool

# Ensure the correct Django settings module is used
os.environ["DJANGO_SETTINGS_MODULE"] = "cms.settings.functional_test"

# This setting is required for Django to run within a Poetry shell
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "True"

# The factory classes require Django to have been set up at their import time.
# To ensure Django set up happens before that point, we call setup at the module level here.
# This will get called again during the test runner setup in the before_all hook,
# but that happens too late to solve import time issues.
django.setup()


def before_all(context: Context):
    """Runs once before all tests.
    Sets up playwright browser and context to be used in all scenarios.
    """
    # Register our django test runner so the entire test run is wrapped in a django test runner
    use_fixture(django_test_runner, context=context)

    context.playwright: Playwright = sync_playwright().start()
    context.playwright_trace = str_to_bool(os.getenv("TRACE", "True"))
    context.playwright_traces_dir = Path(os.getenv("TRACES_DIR", str(Path.cwd().joinpath("tmp_traces"))))

    configure_and_launch_playwright_browser(context)

    if context.playwright_trace:
        context.playwright_traces_dir.mkdir(exist_ok=True)
        # Start the main trace for this browser context, we will record individual scenario traces in chunks
        context.browser_context.tracing.start(screenshots=True, snapshots=True, sources=True)


def configure_and_launch_playwright_browser(context: Context) -> None:
    """Configures and launches a playwright browser and browser context for use in the tests."""
    browser_type = os.getenv("BROWSER", "chromium")
    headless = str_to_bool(os.getenv("HEADLESS", "True"))
    slow_mo = int(os.getenv("SLOW_MO", "0"))
    default_browser_timeout = int(os.getenv("DEFAULT_BROWSER_TIMEOUT", "5_000"))

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

    context.browser_context: BrowserContext = context.browser.new_context()
    context.browser_context.set_default_timeout(default_browser_timeout)


def after_all(context: Context):
    """Runs once after all tests.
    Cleans up playwright objects.
    """
    if context.playwright_trace:
        context.browser_context.tracing.stop()

    context.browser_context.close()
    context.browser.close()
    context.playwright.stop()


def before_scenario(context: Context, scenario: Scenario):
    """Runs before each scenario.
    Create a new playwright page to be used by the scenario, passed through the behave context.
    """
    # Register our django test case fixture so every scenario is wrapped in a Django test case
    use_fixture(django_test_case, context=context)

    context.page: Page = context.browser_context.new_page()

    if context.playwright_trace:
        # Start a new tracing chunk to capture each scenario separately
        context.browser_context.tracing.start_chunk(name=scenario.name, title=scenario.name)


def after_scenario(context: Context, scenario: Scenario):
    """Runs after each scenario.
    Write out a Playwright trace if the scenario failed and trace recording is enabled, then close the playwright page.
    """
    if context.playwright_trace and scenario.status == Status.failed:
        # If the scenario failed, write the trace chunk out to a file, which will be prefixed with the scenario name
        context.browser_context.tracing.stop_chunk(
            path=context.playwright_traces_dir.joinpath(f"{scenario.name.replace(' ', '_')}_failure_trace.zip")
        )

    elif context.playwright_trace:
        # Else end the trace chunk without saving to a file
        context.browser_context.tracing.stop_chunk()

    context.page.close()
