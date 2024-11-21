from .base import *  # noqa: F403  # pylint: disable=wildcard-import,unused-wildcard-import

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


# Silence Slack notifications by default
SLACK_NOTIFICATIONS_WEBHOOK_URL = None
