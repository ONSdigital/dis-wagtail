import os

from behave.model import Scenario
from behave.runner import Context
from playwright.sync_api import Playwright, sync_playwright


def before_all(context: Context):
    """Runs once before all tests.
    Sets up playwright browser and context to be be used in all scenarios.
    """
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

    context.browser_context = context.browser.new_context()
    context.browser_context.set_default_timeout(5_000)


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
    context.page = context.browser.new_page()


def after_scenario(context: Context, _scenario: Scenario):
    """Runs after each scenario."""
    context.page.close()
