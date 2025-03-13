import copy
import os

from .base import *  # noqa: F403  # pylint: disable=wildcard-import,unused-wildcard-import

env = os.environ.copy()

# Debugging to be enabled locally only
DEBUG = True

# This key to be used locally only.
# pragma: allowlist nextline secret
SECRET_KEY = "this_is_not_a_secret_key"  # noqa: S105

ALLOWED_HOSTS = ["*"]

# Allow requests from the local IPs to see more debug information.
INTERNAL_IPS = ("127.0.0.1", "10.0.2.2")

# This is only to test Wagtail emails.
WAGTAILADMIN_BASE_URL = "http://localhost:8000"

# Display sent emails in the console while developing locally.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Disable password validators when developing locally.
AUTH_PASSWORD_VALIDATORS = []

ONS_API_BASE_URL = env.get("ONS_API_BASE_URL", "https://api.beta.ons.gov.uk/v1")


# Enable Wagtail's style guide in Wagtail's settings menu.
# http://docs.wagtail.io/en/stable/contributing/styleguide.html
INSTALLED_APPS += ["wagtail.contrib.styleguide"]  # noqa: F405
INSTALLED_APPS += ["django_migration_linter"]

# Disable forcing HTTPS locally since development server supports HTTP only.
SECURE_SSL_REDIRECT = False
# For the same reason the HSTS header should not be sent.
SECURE_HSTS_SECONDS = 0

# Adds Django Debug Toolbar
INSTALLED_APPS.append("debug_toolbar")
MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")  # noqa: F405
SHOW_TOOLBAR = True  # Override in `local.py`
DEBUG_TOOLBAR_CONFIG = {
    # The default debug_toolbar_middleware.show_toolbar function checks whether the
    # request IP is in settings.INTERNAL_IPS. In Docker, the request IP can vary, so
    # we set it in settings.local instead.
    "SHOW_TOOLBAR_CALLBACK": lambda x: SHOW_TOOLBAR,
    "SHOW_COLLAPSED": True,
}

# Database
DATABASES = {
    "default": dj_database_url.config(default="postgres://ons:ons@localhost:5432/ons"),  # noqa: F405
}
DATABASES["read_replica"] = copy.deepcopy(DATABASES["default"])

# Redis
REDIS_URL = env.get("REDIS_URL", "redis://localhost:6379")
CACHES["default"] = {  # noqa: F405
    "BACKEND": "django_redis.cache.RedisCache",
    "LOCATION": REDIS_URL,
    "OPTIONS": {**redis_options},  # noqa: F405
}

# Django Defender
ENABLE_DJANGO_DEFENDER = False

# PUBLISHER_BACKEND = os.getenv("PUBLISHER_BACKEND", "log")  # Options: log, kafka, none

# Import settings from local.py file if it exists. Please use it to keep
# settings that are not meant to be checked into Git and never check it in.
# pylint: disable=unused-wildcard-import,useless-suppression
try:
    from .local import *  # noqa: F403  # pylint: disable=wildcard-import  # type: ignore[assignment]
except ImportError:
    pass
# pylint: enable=unused-wildcard-import,useless-suppression

MIGRATION_LINTER_OPTIONS = {
    "exclude_apps": [
        "taggit",
        "wagtailcore",
        "wagtailembeds",
        "wagtailimages",
        "wagtailadmin",
        "wagtailsearch",
        "wagtaildocs",
        "wagtailredirects",
        "wagtailusers",
    ],
    "ignore_name": [
        "0002_alter_customdocument_file_size",
        "0004_contactdetails_core_contactdetails_name_unique",
        "0003_delete_tracking",
        "0002_customimage_description",
        "0003_customimage__privacy_and_more",
        "0003_customdocument__privacy_and_more",
        "0002_articleseriespage_listing_image_and_more",  # Ignoring NOT NULL constraint on columns
    ],
}
