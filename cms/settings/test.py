import os

from .base import *  # noqa: F403  # pylint: disable=wildcard-import,unused-wildcard-import
from .base import MIDDLEWARE  # Explicitly import MIDDLEWARE to avoid undefined errors

# #############
# General

# pragma: allowlist nextline secret
SECRET_KEY = "fake_secret_key_to_run_tests"  # noqa: S105

ALLOWED_HOSTS = ["*"]

SILENCED_SYSTEM_CHECKS = [
    # It doesn't matter that STATICFILES_DIRS don't exist in tests
    "staticfiles.W004",
]

# Don't redirect to HTTPS in tests or send the HSTS header
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0


# Quieten down the logging in tests
LOGGING["handlers"]["console"]["class"] = "logging.NullHandler"  # type: ignore[index] # noqa: F405

# Wagtail
WAGTAILADMIN_BASE_URL = "http://testserver"

# Google Tag Manager
GOOGLE_TAG_MANAGER_CONTAINER_ID = "GTM-123456789"

# Cookie banner config
ONS_COOKIE_BANNER_SERVICE_NAME = "example.ons.gov.uk"
MANAGE_COOKIE_SETTINGS_URL = "example.ons.gov.uk/cookies"

# #############
# Performance

# By default, Django uses a computationally difficult algorithm for passwords hashing.
# We don't need such a strong algorithm in tests, so use MD5
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

DEFENDER_DISABLE_USERNAME_LOCKOUT = True
DEFENDER_DISABLE_IP_LOCKOUT = True

# Read replica should mirror the default database during tests.
# https://docs.djangoproject.com/en/stable/topics/testing/advanced/#tests-and-multiple-databases
DATABASES["read_replica"].setdefault("TEST", {"MIRROR": "default"})  # noqa: F405

# Force database connections to be read-only for the replica
if "postgres" in DATABASES["read_replica"]["ENGINE"]:  # noqa: F405
    DATABASES["read_replica"]["ENGINE"] = "cms.core.database_backends.postgres_readonly"  # noqa: F405

# Disable caches in tests
CACHES["default"] = {  # noqa: F405
    "BACKEND": "django.core.cache.backends.dummy.DummyCache",
}

# Enqueue background tasks on commit for tests
# https://docs.wagtail.org/en/latest/releases/6.4.html#background-tasks-run-at-end-of-current-transaction
TASKS = {
    "default": {
        "BACKEND": "django_tasks.backends.immediate.ImmediateBackend",
        "ENQUEUE_ON_COMMIT": False,
    }
}

# Silence Slack notifications by default
SLACK_NOTIFICATIONS_WEBHOOK_URL = None

ONS_API_BASE_URL = "https://dummy_base_api"
ONS_WEBSITE_DATASET_BASE_URL = "https://dummy_datasets/datasets"
KAFKA_SERVERS = os.getenv("KAFKA_SERVERS", "localhost:9094").split(",")

# Ignore proxy count in tests
XFF_STRICT = False

# turn on the real Wagtail login form
WAGTAIL_CORE_ADMIN_LOGIN_ENABLED = True


# We remove ONSAuthMiddleware and re-insert
# Django's built-in AuthenticationMiddleware so that both unit tests and Playwright-based UI tests
# behave correctly.
#
# 1. Unit tests:
#    - AWS_COGNITO_LOGIN_ENABLED=False causes ONSAuthMiddleware.process_request() to call
#      _handle_cognito_disabled(request):
#        • It calls super().process_request(request) first, so request.user is populated from the session.
#        • Then, because Cognito is disabled, it checks: request.user.is_authenticated and
#          not request.user.has_usable_password(). Factory-created test users often have no usable
#          password, so ONSAuthMiddleware immediately logs them out.
#    - If we leave ONSAuthMiddleware in place, a call to self.client.force_login(self.user) will be
#      undone on the very next request, making request.user AnonymousUser and causing every protected
#      view (edit/delete/chooser, etc.) to redirect to /admin/login/ (HTTP 302).
#    - ONSAuthMiddleware inherits from AuthenticationMiddleware. If we remove it without
#      adding back django.contrib.auth.middleware.AuthenticationMiddleware, nothing will ever populate
#      request.user from the session, so force_login() has no effect at all.
#
# 2. Playwright UI tests (auth.js integration):
#    - Under @cognito_enabled, environment.py sets AWS_COGNITO_LOGIN_ENABLED=True for those scenarios.
#    - ONSAuthMiddleware then tries to find and validate real JWT cookies on each request. Our UI tests
#      inject a fake JWT and CSRF token into the browser, expecting auth.js to handle passive-renew flows.
#      But ONSAuthMiddleware sees the fake/ unsigned token as invalid, calls logout(request)/ redirects
#      to /admin/login/, and breaks the test before auth.js can inject <script id="auth-config"> or call
#      /admin/extend-session/.
#    - By stripping out ONSAuthMiddleware entirely, we keep AWS_COGNITO_LOGIN_ENABLED=True so that template
#      and view logic still believe Cognito is on (rendering data-islands, binding passive-renew). But
#      there's no real JWT validation to block us, so our fake token goes unnoticed.
#    - We must also re-insert AuthenticationMiddleware so that Playwright's login steps (which set a Django
#      session) produce a valid request.user on subsequent requests.
#
# Removing ONSAuthMiddleware and re-adding the built-in AuthenticationMiddleware ensures:
#  • Unit tests do not log out factory-created users without a password, and force_login() works as intended.
#  • Playwright UI tests can inject fake JWTs without being rejected, while views still render Cognito-enabled
#    code paths (data-island, passive-renew, etc.), and request.user stays logged in via the session cookie.

# Remove ONSAuthMiddleware so that neither unit tests nor UI tests get logged out or redirected by JWT logic.
MIDDLEWARE = [mw for mw in MIDDLEWARE if mw != "cms.auth.middleware.ONSAuthMiddleware"]

if "django.contrib.auth.middleware.AuthenticationMiddleware" not in MIDDLEWARE:
    idx = MIDDLEWARE.index("django.contrib.sessions.middleware.SessionMiddleware")
    MIDDLEWARE.insert(
        idx + 1,
        "django.contrib.auth.middleware.AuthenticationMiddleware",
    )
