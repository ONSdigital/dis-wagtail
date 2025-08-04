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

# Display sent emails in via mailpit @ http://localhost:8025
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env.get("EMAIL_HOST", "localhost")
EMAIL_PORT = 1025
EMAIL_USE_TLS = False

# Sender address for email notifications
DEFAULT_FROM_EMAIL = "cms@example.com"

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

SHOW_TOOLBAR = True  # Override in local.py

# Adds Django Debug Toolbar
if DEBUG:
    INSTALLED_APPS.append("debug_toolbar")
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")  # noqa: F405
    DEBUG_TOOLBAR_CONFIG = {
        # The default debug_toolbar_middleware.show_toolbar function checks whether the
        # request IP is in settings.INTERNAL_IPS. In Docker, the request IP can vary, so
        # we set it in settings.local instead.
        "SHOW_TOOLBAR_CALLBACK": lambda x: SHOW_TOOLBAR,
        "SHOW_COLLAPSED": True,
    }

# Force database connections to be read-only for the replica
if "postgres" in DATABASES["read_replica"]["ENGINE"]:  # noqa: F405
    DATABASES["read_replica"]["ENGINE"] = "cms.core.database_backends.postgres_readonly"  # noqa: F405

# Redis
REDIS_URL = env.get("REDIS_URL", "redis://localhost:6379")
CACHES["default"] = {  # noqa: F405
    "BACKEND": "django_redis.cache.RedisCache",
    "LOCATION": REDIS_URL,
    "OPTIONS": {**redis_options},  # noqa: F405
}

# Django Defender
ENABLE_DJANGO_DEFENDER = False

# Auth
SERVICE_AUTH_TOKEN = "wagtail-test-auth-token"  # noqa: S105 - Dummy token matching config in dis-authentication-stub
WAGTAIL_CORE_ADMIN_LOGIN_ENABLED = True
AUTH_STUB_URL = "http://localhost:29500"
AWS_COGNITO_USER_POOL_ID = "dis-authentication-stub"
AWS_COGNITO_APP_CLIENT_ID = "dis-authentication-stub"
IDENTITY_API_BASE_URL = env.get("IDENTITY_API_BASE_URL", f"{AUTH_STUB_URL}/v1")
AUTH_TOKEN_REFRESH_URL = env.get("AUTH_TOKEN_REFRESH_URL", f"{AUTH_STUB_URL}/tokens/self")

if AWS_COGNITO_LOGIN_ENABLED:  # noqa: F405
    WAGTAILADMIN_LOGIN_URL = env.get("WAGTAILADMIN_LOGIN_URL", f"{AUTH_STUB_URL}/florence/login")
    LOGOUT_REDIRECT_URL = env.get("LOGOUT_REDIRECT_URL", f"{AUTH_STUB_URL}/florence/logout")
    AWS_REGION = "eu-west-2"
else:
    SESSION_COOKIE_AGE = 60 * 60 * 24  # 1 day in seconds

# Set auth stub as a trusted origin
CSRF_TRUSTED_ORIGINS = env.get("CSRF_TRUSTED_ORIGINS", AUTH_STUB_URL).split(",")

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
        "0003_releasecalendarpage_datasets",
        "0004_topicpage_headline_figures",
        "0003_footermenu_locale_footermenu_translation_key_and_more",  # Ignoring NOT NULL constraint on columns
        "0007_remove_glossaryterm_core_glossary_term_name_unique_and_more",  # Ignoring NOT NULL constraint
        "0004_make_release_date_mandatory_and_rename_next_release_text",  # Ignoring NOT NULL and RENAMING constraints
        "0004_statisticalarticlepage_headline_figures_figure_ids",
        "0006_statisticalarticlepage_dataset_sorting_and_more",  # Ignoring NOT NULL constraint
        "0006_topicpage_datasets",  # Ignoring NOT NULL constraint
        "0004_bundleteam_preview_notification_sent",  # Ignoring NOT NULL constraint
        "0005_bundle_updated_at",  # Ignoring NOT NULL constraint
        "0007_statisticalarticlepage_featured_chart_content_and_more",  # Ignoring NOT NULL constraint
        "0008_delete_systemmessagessettings",  # Ignoring dropping table
    ],
}

# Blank out build information during local development
BUILD_TIME = None
GIT_COMMIT = None
TAG = "dev"
