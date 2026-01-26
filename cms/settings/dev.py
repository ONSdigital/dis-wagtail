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
WEB_PORT = env.get("WEB_PORT", "8000")
WAGTAILADMIN_BASE_URL = f"http://localhost:{WEB_PORT}"

# Display sent emails in via mailpit @ http://localhost:8025
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env.get("EMAIL_HOST", "localhost")
EMAIL_PORT = int(env.get("MAILPIT_SMTP_PORT", "1025"))
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

DB_PORT = env.get("DB_PORT", "5432")
DATABASES["default"]["PORT"] = DB_PORT  # noqa: F405
DATABASES["read_replica"]["PORT"] = DB_PORT  # noqa: F405

# Force database connections to be read-only for the replica
if "postgres" in DATABASES["read_replica"]["ENGINE"]:  # noqa: F405
    DATABASES["read_replica"]["ENGINE"] = "cms.core.database_backends.postgres_readonly"  # noqa: F405

# Redis
REDIS_PORT = env.get("REDIS_PORT", "6379")
REDIS_URL = env.get("REDIS_URL", f"redis://localhost:{REDIS_PORT}")
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

# External search service
SEARCH_INDEX_PUBLISHER_BACKEND = "kafka"
KAFKA_PORT = env.get("KAFKA_PORT", "9094")
KAFKA_SERVERS = env.get("KAFKA_SERVERS", f"localhost:{KAFKA_PORT}").split(",")

if AWS_COGNITO_LOGIN_ENABLED:  # noqa: F405
    WAGTAILADMIN_LOGIN_URL = env.get("WAGTAILADMIN_LOGIN_URL", f"{AUTH_STUB_URL}/florence/login")
    LOGOUT_REDIRECT_URL = env.get("LOGOUT_REDIRECT_URL", f"{AUTH_STUB_URL}/florence/logout")
    AWS_REGION = "eu-west-2"
else:
    SESSION_COOKIE_AGE = 60 * 60 * 24  # 1 day in seconds

# Set auth stub as a trusted origin
CSRF_TRUSTED_ORIGINS = env.get("CSRF_TRUSTED_ORIGINS", AUTH_STUB_URL).split(",")


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
        "0007_topicpagerelatedarticle_external_url_and_more",  # Ignoring NOT NULL constraint
        "0006_bundle_bundle_api_id_bundledataset_content_api_id",  # Ignoring NOT NULL constraint
        "0002_alter_dataset_version",
        "0008_topicpage_time_series",  # Ignoring NOT NULL constraint
        "0003_topic_slug",  # Ignoring NOT NULL constraint
        "0007_rename_bundle_api_content_id_bundle_bundle_api_bundle_id",  # Ignoring RENAMING constraint
        "0010_rename_glossaryterm_to_definition",  # Ignoring RENAMING table (GlossaryTerm -> Definition)
    ],
}

# Blank out build information during local development
BUILD_TIME = None
GIT_COMMIT = None
TAG = "dev"

# Allow to override but default to enabled
CMS_RESOURCES_ENDPOINT_ENABLED = env.get("CMS_RESOURCES_ENDPOINT_ENABLED", "true").lower() == "true"
USE_I18N_ROOT_NO_TRAILING_SLASH = env.get("USE_I18N_ROOT_NO_TRAILING_SLASH", "true").lower() == "true"

# Domain-based locale configuration
CMS_USE_SUBDOMAIN_LOCALES = env.get("CMS_USE_SUBDOMAIN_LOCALES", "False").lower() == "true"

# -----------------------------------------------------------------------------
# ⚠️ DO NOT EDIT BELOW THIS LINE
# -----------------------------------------------------------------------------
# Import settings from local.py if it exists.
# This is used for local overrides (e.g. developer-specific or untracked secrets).
# Do NOT check local.py into Git, and do NOT add new configuration here.
# All new settings or environment-based configuration should be added ABOVE this block.
# -----------------------------------------------------------------------------
# pylint: disable=unused-wildcard-import,useless-suppression
try:
    from .local import *  # noqa: F403  # pylint: disable=wildcard-import  # type: ignore[assignment]
except ImportError:
    pass
