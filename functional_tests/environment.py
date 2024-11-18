import os

from behave import use_fixture
from behave.model import Scenario
from behave.runner import Context
from django.db import close_old_connections
from playwright.sync_api import BrowserContext, Page, Playwright, sync_playwright

from functional_tests.behave_fixtures import django_test_case, django_test_runner


def before_all(context: Context):
    """Runs once before all tests.
    Sets up playwright browser and context to be used in all scenarios.
    """
    # Register our django test runner so the entire test run is wrapped in a django test runner
    use_fixture(django_test_runner, context=context)

    context.playwright: Playwright = sync_playwright().start()
    browser_type = os.getenv("BROWSER", "chromium")
    headless = os.getenv("HEADLESS", "True") == "True"
    slowmo = int(os.getenv("SLOWMO", "0"))

    browser_kwargs = {
        "headless": headless,
        "slow_mo": slowmo,
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
    context.browser_context.set_default_timeout(10_000)


def after_all(context: Context):
    """Runs once after all tests.
    Cleans up playwright browser context.
    """
    context.browser_context.close()
    context.browser.close()
    context.playwright.stop()


def before_scenario(context: Context, _scenario: Scenario):
    """Runs before each scenario.
    Create a new playwright page to be used by the scenario, through the context.
    """
    # Register our django test case fixture so every scenario is wrapped in a Django test case
    use_fixture(django_test_case, context=context)

    context.page: Page = context.browser.new_page()


def after_scenario(context: Context, _scenario: Scenario):
    """Runs after each scenario.
    Close the playwright page and tidy up any DB connections so they don't block the database teardown.
    """
    context.page.close()

    # Prevent any remaining connections from blocking teardown
    close_old_connections()
