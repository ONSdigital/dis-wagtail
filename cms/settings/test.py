import os

from .base import *  # noqa: F403  # pylint: disable=wildcard-import,unused-wildcard-import

env = os.environ.copy()

# #############
# General

# pragma: allowlist nextline secret
SECRET_KEY = "fake_secret_key_to_run_tests"  # noqa: S105

ALLOWED_HOSTS = ["*"]

SILENCED_SYSTEM_CHECKS = [
    # It doesn't matter that STATICFILES_DIRS don't exist in tests
    "staticfiles.W004",
]

TEST_RUNNER = "cms.core.tests.runner.OldConnectionsCleanupDiscoveryRunner"

# Don't redirect to HTTPS in tests or send the HSTS header
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0


# Quieten down the logging in tests
LOGGING["handlers"]["console"]["class"] = "logging.NullHandler"  # type: ignore[index] # noqa: F405

# Wagtail
WAGTAILADMIN_BASE_URL = "http://testserver"

# Google Tag Manager
GOOGLE_TAG_MANAGER_CONTAINER_ID = "GTM-123456789"

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

# Explicitly set the ImmediateBackend for tasks (even though it is the default)
TASKS = {
    "default": {
        "BACKEND": "django_tasks.backends.immediate.ImmediateBackend",
    }
}

# Silence Slack notifications by default
SLACK_NOTIFICATIONS_WEBHOOK_URL = None

ONS_API_BASE_URL = "https://dummy_base_api"
DATASETS_BASE_API_URL = "https://dummy_base_api/datasets"
KAFKA_SERVERS = env.get("KAFKA_SERVERS", "localhost:9094").split(",")

# Ignore proxy count in tests
XFF_STRICT = False

# turn on the real Wagtail login form
WAGTAIL_CORE_ADMIN_LOGIN_ENABLED = True


# Setting dummy environment variables for credentials and region in our test setup for the S3 storage tests.
AWS_STORAGE_BUCKET_NAME = "test-bucket"
AWS_S3_REGION_NAME = "us-east-1"
AWS_ACCESS_KEY_ID = "testing"
AWS_SECRET_ACCESS_KEY = "testing"  # noqa: S105
AWS_SESSION_TOKEN = "testing"  # noqa: S105
AWS_EC2_METADATA_DISABLED = True

USE_I18N_ROOT_NO_TRAILING_SLASH = True


# Ensure cms.frontend_cache is install
if "cms.frontend_cache" not in INSTALLED_APPS:  # noqa: F405
    INSTALLED_APPS.append("cms.frontend_cache")  # noqa: F405
