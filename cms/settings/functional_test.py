import copy

from .base import *  # noqa: F403  # pylint: disable=wildcard-import,unused-wildcard-import

# Debugging to be enabled locally only
DEBUG = True

# This key to be used locally only.
# pragma: allowlist nextline secret
SECRET_KEY = "dummy_functional_test_secret_key"  # noqa: S105

ALLOWED_HOSTS = ["*"]

# Allow requests from the local IPs to see more debug information.
INTERNAL_IPS = ("127.0.0.1", "10.0.2.2")


# This is only to test Wagtail emails.
WAGTAILADMIN_BASE_URL = "http://localhost:8000"


# Display sent emails in the console while developing locally.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"


# Disable password validators when developing locally.
AUTH_PASSWORD_VALIDATORS = []

# Disable forcing HTTPS locally since development server supports HTTP only.
SECURE_SSL_REDIRECT = False
# For the same reason the HSTS header should not be sent.
SECURE_HSTS_SECONDS = 0

# By default, Django uses a computationally difficult algorithm for passwords hashing.
# We don't need such a strong algorithm in tests, so use MD5
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

DATABASES = {
    "default": dj_database_url.config(default="postgres://ons:ons@localhost:15432/ons"),  # noqa: F405
}
DATABASES["read_replica"] = copy.deepcopy(DATABASES["default"])

REDIS_URL = "redis://localhost:16379"
