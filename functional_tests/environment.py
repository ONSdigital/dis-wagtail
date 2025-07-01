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

import importlib
import base64


def before_all(context: Context):
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


def configure_and_launch_playwright_browser(context: Context) -> None:
    """Configures and launches a playwright browser and browser context for use in the tests."""
    browser_type = os.getenv("PLAYWRIGHT_BROWSER", "chromium")
    headless = str_to_bool(os.getenv("PLAYWRIGHT_HEADLESS", "False"))
    slow_mo = int(os.getenv("PLAYWRIGHT_SLOW_MO", "500"))
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


def after_all(context: Context):
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


def before_scenario(context: Context, scenario: Scenario):
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

    context.page = context.playwright_context.new_page()

    # Set the page to the context so it can be used in steps and it can help with debugging auth.js errors
    # and dis-authorisation-client-js library errors
    context.page.on("console", lambda msg: print(f"[PAGE][{msg.type}] {msg.text}"))

    if context.playwright_trace:
        # Start a new tracing chunk to capture each scenario separately
        context.playwright_context.tracing.start_chunk(name=scenario.name, title=scenario.name)


def after_scenario(context: Context, scenario: Scenario):
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

    context.page.close()


def before_tag(context: Context, tag: str):
    if tag == "cognito_enabled":
        print("\n=== ENABLING COGNITO ===")

        # Import after Django setup
        from cms.auth import utils as auth_utils
        from cms.auth.tests.helpers import generate_rsa_keypair

        # Apply settings
        context.aws_override = override_settings(
            # Core settings
            DEBUG=True,  # Enable debug for better error messages
            AWS_COGNITO_LOGIN_ENABLED=True,
            AWS_COGNITO_APP_CLIENT_ID="test-client-id",
            AWS_REGION="eu-west-2",
            AWS_COGNITO_USER_POOL_ID="test-pool",
            IDENTITY_API_BASE_URL="https://cognito-idp.eu-west-2.amazonaws.com/test-pool",
            ACCESS_TOKEN_COOKIE_NAME="access_token",
            ID_TOKEN_COOKIE_NAME="id",
            AUTH_TOKEN_REFRESH_URL="/refresh/",
            SESSION_RENEWAL_OFFSET_SECONDS=3,
            WAGTAIL_CORE_ADMIN_LOGIN_ENABLED=True,
            WAGTAILADMIN_HOME_PATH="admin/",
            CSRF_COOKIE_NAME="csrftoken",
            CSRF_HEADER_NAME="HTTP_X_CSRFTOKEN",
            PUBLISHING_ADMIN_GROUP_NAME="Publishing Admins",
            PUBLISHING_OFFICER_GROUP_NAME="Publishing Officers",
            VIEWERS_GROUP_NAME="Viewers",
        )
        context.aws_override.enable()

        # FORCE HOOK REGISTRATION
        # Since the hook registration is conditional on AWS_COGNITO_LOGIN_ENABLED,
        # and that was False at import time, we need to manually register the hook
        from wagtail import hooks as wagtail_hooks
        from django.utils.html import format_html, json_script
        from django_jinja.builtins.filters import static
        from cms.auth.utils import get_auth_config

        # Define the hook function directly
        @wagtail_hooks.register("insert_global_admin_js")
        def global_admin_auth_js() -> str:
            """Insert a safe JSON payload and defer-loaded bundle into the Wagtail admin."""
            config_tag = json_script(get_auth_config(), element_id="auth-config")
            return format_html(
                '{}<script src="{}" defer></script>',
                config_tag,
                static("js/auth.js"),
            )

        print("Manually registered global_admin_auth_js hook")

        print("Settings applied:")
        print(f"  AWS_COGNITO_LOGIN_ENABLED: {django.conf.settings.AWS_COGNITO_LOGIN_ENABLED}")
        print(f"  AWS_COGNITO_APP_CLIENT_ID: {django.conf.settings.AWS_COGNITO_APP_CLIENT_ID}")

        # Generate test keypair
        context.test_keypair = generate_rsa_keypair()
        public_b64 = base64.b64encode(context.test_keypair.public_der).decode()
        context.test_jwks = {context.test_keypair.kid: public_b64}

        print(f"Generated keypair with KID: {context.test_keypair.kid}")

        # Mock get_jwks
        importlib.reload(auth_utils)
        context.original_get_jwks = auth_utils.get_jwks
        auth_utils.get_jwks = lambda: context.test_jwks
        print("Mocked get_jwks function")


def after_tag(context: Context, tag: str):
    if tag == "cognito_enabled" and hasattr(context, "aws_override"):
        print("\n=== DISABLING COGNITO ===")

        from cms.auth import utils as auth_utils

        context.aws_override.disable()

        if hasattr(context, "original_get_jwks"):
            auth_utils.get_jwks = context.original_get_jwks

        importlib.reload(auth_utils)  # functional_tests/environment_debug.py


# Minimal environment for debugging auth issues
