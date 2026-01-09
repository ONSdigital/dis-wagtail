# pylint: disable=too-many-lines
"""Django settings for ons project."""

import datetime
import os
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, cast

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _
from django_jinja.builtins import DEFAULT_EXTENSIONS

from cms.core.elasticache import ElastiCacheIAMCredentialProvider
from cms.core.jinja2 import custom_json_dumps

env = os.environ.copy()

# Build paths inside the project like this: BASE_DIR / "something"

PROJECT_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = PROJECT_DIR.parent


# Switch off DEBUG mode explicitly in the base settings.
# https://docs.djangoproject.com/en/stable/ref/settings/#debug
DEBUG = False

# Secret key is important to be kept secret. Never share it with anyone. Please
# always set it in the environment variable and never check into the
# repository.
# In its default template Django generates a 50-characters long string using
# the following function:
# https://github.com/django/django/blob/fd8a7a5313f5e223212085b2e470e43c0047e066/django/core/management/utils.py#L76-L81
# https://docs.djangoproject.com/en/stable/ref/settings/#allowed-hosts
if "SECRET_KEY" in env:
    SECRET_KEY = env["SECRET_KEY"]

IS_EXTERNAL_ENV = os.environ.get("IS_EXTERNAL_ENV", "false").lower() == "true"


# Define what hosts an app can be accessed by.
# It will return HTTP 400 Bad Request error if your host is not set using this
# setting.
# https://docs.djangoproject.com/en/stable/ref/settings/#allowed-hosts
if "ALLOWED_HOSTS" in env:
    ALLOWED_HOSTS = env["ALLOWED_HOSTS"].split(",")

# A list of trusted origins for unsafe requests (e.g. POST).
# For requests that include the Origin header,
# Django's CSRF protection requires that header match
# the origin present in the Host header.
# Important: values must include the scheme (e.g. https://) and the hostname
# https://docs.djangoproject.com/en/stable/ref/settings/#csrf-trusted-origins
if "CSRF_TRUSTED_ORIGINS" in env:
    CSRF_TRUSTED_ORIGINS = env["CSRF_TRUSTED_ORIGINS"].split(",")

# Application definition

INSTALLED_APPS = [
    "cms.articles",
    "cms.auth",
    "cms.bundles",
    "cms.core",
    "cms.datasets",
    "cms.datavis",
    "cms.documents",
    "cms.home",
    "cms.images",
    "cms.private_media",
    "cms.release_calendar",
    "cms.teams",
    "cms.themes",
    "cms.topics",
    "cms.users",
    "cms.standard_pages",
    "cms.methodology",
    "cms.navigation",
    "cms.taxonomy",
    "cms.search",
    "cms.workflows",
    "wagtail.sites",
    "wagtail.users",
    "wagtail.snippets",
    "wagtail.documents",
    "wagtail.images",
    "wagtail.search",
    "wagtail.admin",
    "wagtail.locales",
    "wagtailschemaorg",
    "wagtail.contrib.settings",
    "wagtail.contrib.redirects",
    "wagtail.contrib.legacy.richtext",
    "wagtail.contrib.table_block",
    "wagtail.contrib.simple_translation",
    "wagtail",
    "modelcluster",
    "taggit",
    "django_extensions",
    "django.contrib.auth",  # Wagtail requires the auth app be installed, even if it's not used.
    "django.contrib.contenttypes",
    "whitenoise.runserver_nostatic",  # Must be before `django.contrib.staticfiles`
    "django.contrib.staticfiles",
    "django_jinja",
    "wagtailmath",
    "wagtailtables",
    "wagtailfontawesomesvg",
    "wagtail_tinytableblock",
    "rest_framework",
]

if not IS_EXTERNAL_ENV:
    INSTALLED_APPS.extend(
        [
            "django.contrib.admin",
            "django.contrib.sessions",
            "django.contrib.messages",
        ]
    )


# Middleware classes
# https://docs.djangoproject.com/en/stable/ref/settings/#middleware
# https://docs.djangoproject.com/en/stable/topics/http/middleware/
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Whitenoise middleware is used to server static files (CSS, JS, etc.).
    # According to the official documentation it should be listed underneath
    # SecurityMiddleware.
    # http://whitenoise.evans.io/en/stable/#quickstart-for-django-apps
    "cms.core.whitenoise.CMSWhiteNoiseMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Custom middleware to redirect trailing slash URLs to non-trailing-slash equivalent
    # which needs to be placed after CommonMiddleware to avoid double redirects.
    "cms.core.middleware.NonTrailingSlashRedirectMiddleware",
    "wagtail.contrib.redirects.middleware.RedirectMiddleware",
]

# Some middleware isn't needed for a external environment.
# Disable them to improve performance
if not IS_EXTERNAL_ENV:
    common_middleware_index = MIDDLEWARE.index("django.middleware.common.CommonMiddleware")
    MIDDLEWARE.insert(common_middleware_index, "django.contrib.messages.middleware.MessageMiddleware")
    MIDDLEWARE.insert(common_middleware_index, "cms.auth.middleware.ONSAuthMiddleware")
    MIDDLEWARE.insert(common_middleware_index, "django.contrib.sessions.middleware.SessionMiddleware")
    MIDDLEWARE.insert(common_middleware_index, "xff.middleware.XForwardedForMiddleware")

ROOT_URLCONF = "cms.urls"

context_processors = [
    "django.template.context_processors.debug",
    "django.template.context_processors.request",
    "wagtail.contrib.settings.context_processors.settings",
    # This is a custom context processor that lets us add custom
    # global variables to all the templates.
    "cms.core.context_processors.global_vars",
]

if not IS_EXTERNAL_ENV:
    context_processors.extend(
        [
            "django.contrib.messages.context_processors.messages",
            "django.contrib.auth.context_processors.auth",
        ]
    )

TEMPLATES = [
    {
        "BACKEND": "django_jinja.jinja2.Jinja2",
        "DIRS": [
            PROJECT_DIR / "jinja2",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "match_extension": ".html",
            "app_dirname": "jinja2",
            "undefined": "jinja2.ChainableUndefined",
            "context_processors": context_processors,
            "extensions": [
                *DEFAULT_EXTENSIONS,
                "wagtail.jinja2tags.core",
                "wagtail.admin.jinja2tags.userbar",
                "wagtail.images.jinja2tags.images",
                "wagtail.contrib.settings.jinja2tags.settings",
                "cms.core.jinja2tags.CoreExtension",
                "cms.navigation.jinja2tags.NavigationExtension",
                "wagtailschemaorg.jinja2tags.WagtailSchemaOrgExtension",
            ],
            "policies": {
                # https://jinja.palletsprojects.com/en/stable/api/#policies
                "json.dumps_function": custom_json_dumps,
            },
        },
    },
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": context_processors,
        },
        "DIRS": [
            PROJECT_DIR / "jinja2" / "assets" / "icons",  # for icons registered with register_icons
        ],
    },
]

WSGI_APPLICATION = "cms.wsgi.application"

AWS_REGION = env.get("AWS_REGION")


# Database

# None allows connections to be reused for longer, since opening them is expensive.
# CONN_HEALTH_CHECK ensures they're still healthy before attempting to use them.
db_conn_max_age = int(env["PG_CONN_MAX_AGE"]) if "PG_CONN_MAX_AGE" in env else None
db_read_conn_max_age = int(env["PG_READ_CONN_MAX_AGE"]) if "PG_READ_CONN_MAX_AGE" in env else None

if "PG_DB_ADDR" in env:
    # Use IAM authentication to connect to the Database
    DATABASES = {
        "default": cast(
            dj_database_url.DBConfig,
            {
                "ENGINE": "django_iam_dbauth.aws.postgresql",
                "NAME": env["PG_DB_DATABASE"],
                "USER": env["PG_DB_USER"],
                "HOST": env["PG_DB_ADDR"],
                "PORT": env["PG_DB_PORT"],
                "CONN_MAX_AGE": db_conn_max_age,
                "CONN_HEALTH_CHECK": True,
                "OPTIONS": {"use_iam_auth": True, "sslmode": "require", "region_name": AWS_REGION},
            },
        )
    }

    # Additionally configure a read-replica
    if "PG_DB_READ_ADDR" in env:
        DATABASES["read_replica"] = {
            **deepcopy(DATABASES["default"]),
            "HOST": env["PG_DB_READ_ADDR"],
            "CONN_MAX_AGE": db_read_conn_max_age,
        }

else:
    # note: dj_database_url.config() expects an int, while dj_database_url.DBConfig accepts None
    DATABASES = {
        "default": dj_database_url.config(
            conn_max_age=db_conn_max_age or 0, conn_health_checks=True, default="postgres://ons:ons@localhost:5432/ons"
        ),
    }

    if "READ_REPLICA_DATABASE_URL" in env:
        DATABASES["read_replica"] = dj_database_url.config(
            env="READ_REPLICA_DATABASE_URL", conn_max_age=db_read_conn_max_age or 0
        )

if "read_replica" not in DATABASES:
    DATABASES["read_replica"] = deepcopy(DATABASES["default"])

DATABASE_ROUTERS = [
    "cms.core.db_router.ExternalEnvRouter",
    "cms.core.db_router.ReadReplicaRouter",
]

# Server-side cache settings. Do not confuse with front-end cache.
# https://docs.djangoproject.com/en/stable/topics/cache/
# If the server has a Redis instance exposed via a URL string in the REDIS_URL
# environment variable, prefer that. Otherwise, use the database backend. We
# usually use Redis in production and database backend on staging and dev. In
# order to use database cache backend you need to run
# "django-admin createcachetable" to create a table for the cache.
#
# Do not use the same Redis instance for other things like Celery!

CACHES: dict = {
    "memory": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "memory",
    }
}

redis_options = {
    "IGNORE_EXCEPTIONS": True,
    "SOCKET_CONNECT_TIMEOUT": 2,  # seconds
    "SOCKET_TIMEOUT": 2,  # seconds
}
DJANGO_REDIS_LOG_IGNORED_EXCEPTIONS = True

# Prefer the TLS connection URL over non for Heroku
if redis_url := env.get("REDIS_TLS_URL", env.get("REDIS_URL")):
    connection_pool_kwargs: dict = {}

    if redis_url.startswith("rediss"):
        # Heroku Redis uses self-signed certificates for secure redis connections. https://stackoverflow.com/a/66286068
        # When using TLS, we need to disable certificate validation checks.
        connection_pool_kwargs["ssl_cert_reqs"] = None

    CACHES["default"] = {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": redis_url,
        "OPTIONS": {**redis_options, "CONNECTION_POOL_KWARGS": connection_pool_kwargs},
    }

elif elasticache_addr := env.get("ELASTICACHE_ADDR"):
    port = env["ELASTICACHE_PORT"]

    if AWS_REGION is None:
        raise ImproperlyConfigured("AWS_REGION must be defined to use Elasticache.")

    CACHES["default"] = {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"rediss://{elasticache_addr}:{port}",
        "OPTIONS": {
            **redis_options,
            "CONNECTION_POOL_KWARGS": {
                "credential_provider": ElastiCacheIAMCredentialProvider(
                    user=env["ELASTICACHE_USER_NAME"],
                    cluster_name=env["ELASTICACHE_CLUSTER_NAME"],
                    region=AWS_REGION,
                )
            },
        },
    }
else:
    CACHES["default"] = {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "database_cache",
    }

# Search
# https://docs.wagtail.io/en/latest/topics/search/backends.html

WAGTAILSEARCH_BACKENDS = {"default": {"BACKEND": "wagtail.search.backends.database"}}


# Password validation
# https://docs.djangoproject.com/en/stable/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

if IS_EXTERNAL_ENV:
    AUTHENTICATION_BACKENDS: list[str] = []


# Internationalization
# https://docs.djangoproject.com/en/stable/topics/i18n/

TIME_ZONE = "Europe/London"
USE_TZ = True

USE_I18N = True
WAGTAIL_I18N_ENABLED = True

LANGUAGE_CODE = "en-gb"
WAGTAIL_CONTENT_LANGUAGES = LANGUAGES = [
    ("en-gb", _("English")),
    ("cy", _("Welsh")),
]

_valid_language_codes = {code for code, _ in LANGUAGES}

LOCALE_PATHS = [PROJECT_DIR / "locale"]

# User groups
PUBLISHING_ADMINS_GROUP_NAME = "Publishing Admins"
PUBLISHING_OFFICERS_GROUP_NAME = "Publishing Officers"
VIEWERS_GROUP_NAME = "Viewers"


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/stable/howto/static-files/

# We serve static files with Whitenoise (set in MIDDLEWARE). It also comes with
# a custom backend for the static files storage. It makes files cacheable
# (cache-control headers) for a long time and adds hashes to the file names,
# e.g. main.css -> main.1jasdiu12.css.
# The static files with this backend are generated when you run
# "django-admin collectstatic".
# http://whitenoise.evans.io/en/stable/#quickstart-for-django-apps
# https://docs.djangoproject.com/en/stable/ref/settings/#std-setting-STORAGES
STORAGES = {
    "default": {"BACKEND": "cms.private_media.storages.AccessControlLoggingFileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}


# This is where Django will look for static files outside the directories of
# applications which are used by default.
# https://docs.djangoproject.com/en/stable/ref/settings/#staticfiles-dirs
STATICFILES_DIRS = [
    # "static_compiled" is a folder used by the front-end tooling
    # to output compiled static assets.
    (PROJECT_DIR / "jinja2" / "assets"),
    (PROJECT_DIR / "static_compiled"),
]


# This is where Django will put files collected from application directories
# and custom directories set in "STATICFILES_DIRS" when
# using "django-admin collectstatic" command.
# https://docs.djangoproject.com/en/stable/ref/settings/#static-root
STATIC_ROOT = env.get("STATIC_DIR", BASE_DIR / "static")


# This is the URL that will be used when serving static files, e.g.
# https://llamasavers.com/static/
# https://docs.djangoproject.com/en/stable/ref/settings/#static-url
STATIC_URL = env.get("STATIC_URL", "/static/")


# Where in the filesystem the media (user uploaded) content is stored.
# MEDIA_ROOT is not used when S3 backend is set up.
# Probably only relevant to the local development.
# https://docs.djangoproject.com/en/stable/ref/settings/#media-root
MEDIA_ROOT = env.get("MEDIA_DIR", BASE_DIR / "media")


# The URL path that media files will be accessible at. This setting won't be
# used if S3 backend is set up.
# Probably only relevant to the local development.
# https://docs.djangoproject.com/en/stable/ref/settings/#media-url
MEDIA_URL = env.get("MEDIA_URL", "/media/")


# AWS S3 buckets configuration
# This is media files storage backend configuration. S3 is our preferred file
# storage solution.
# To enable this storage backend we use django-storages package...
# https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html
# ...that uses AWS' boto3 library.
# https://boto3.amazonaws.com/v1/documentation/api/latest/index.html
#
# Three required environment variables are:
#  * AWS_STORAGE_BUCKET_NAME
# https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html#environment-variables
if "AWS_STORAGE_BUCKET_NAME" in env:
    # Add django-storages to the installed apps
    INSTALLED_APPS += ["storages"]

    # https://docs.djangoproject.com/en/stable/ref/settings/#std-setting-STORAGES
    STORAGES["default"]["BACKEND"] = "cms.private_media.storages.AccessControlledS3Storage"

    AWS_STORAGE_BUCKET_NAME = env["AWS_STORAGE_BUCKET_NAME"]

    # Disables signing of the S3 objects' URLs. When set to True it
    # will append authorization querystring to each URL.
    AWS_QUERYSTRING_AUTH = False

    # Do not allow overriding files on S3 as per Wagtail docs recommendation:
    # https://docs.wagtail.io/en/stable/advanced_topics/deploying.html#cloud-storage
    # Not having this setting may have consequences in losing files.
    AWS_S3_FILE_OVERWRITE = False

    # Default ACL for new files should be "private" - not accessible to the
    # public.
    AWS_DEFAULT_ACL = "private"

    # Limit how large a file can be spooled into memory before it's written to disk.
    AWS_S3_MAX_MEMORY_SIZE = 2 * 1024 * 1024  # 2MB

    # We generally use this setting in the production to put the S3 bucket
    # behind a CDN using a custom domain, e.g. media.llamasavers.com.
    # https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html#cloudfront
    if "AWS_S3_CUSTOM_DOMAIN" in env:
        AWS_S3_CUSTOM_DOMAIN = env["AWS_S3_CUSTOM_DOMAIN"]

    # When signing URLs is facilitated, the region must be set, because the
    # global S3 endpoint does not seem to support that. Set this only if
    # necessary.
    if "AWS_S3_REGION_NAME" in env:
        AWS_S3_REGION_NAME = env["AWS_S3_REGION_NAME"]

    # This settings lets you force using http or https protocol when generating
    # the URLs to the files. Set https as default.
    # https://github.com/jschneier/django-storages/blob/10d1929de5e0318dbd63d715db4bebc9a42257b5/storages/backends/s3boto3.py#L217
    AWS_S3_URL_PROTOCOL = env.get("AWS_S3_URL_PROTOCOL", "https:")

PRIVATE_MEDIA_BULK_UPDATE_MAX_WORKERS = env.get("PRIVATE_MEDIA_BULK_UPDATE_MAX_WORKERS", 5)

# Logging
# This logging is configured to be used with Sentry and console logs. Console
# logs are widely used by platforms offering Docker deployments, e.g. Heroku.
# We use Sentry to only send error logs so we're notified about errors that are
# not Python exceptions.
# We do not use default mail or file handlers because they are of no use for
# us.
# https://docs.djangoproject.com/en/stable/topics/logging/
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        # Send logs with at least INFO level to the console.
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
        "gunicorn_access": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "gunicorn_json",
        },
    },
    "formatters": {
        "verbose": {"format": "[%(asctime)s][%(process)d][%(levelname)s][%(name)s] %(message)s"},
        "json": {
            "()": "cms.core.logs.JSONFormatter",
        },
        "gunicorn_json": {
            "()": "cms.core.logs.GunicornJsonFormatter",
        },
    },
    "loggers": {
        "cms": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "cms.audit": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "wagtail": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "apscheduler": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "xff": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "gunicorn.access": {
            "handlers": ["gunicorn_access"],
            "level": "INFO",
            "propagate": False,
        },
        "gunicorn.error": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}


# Email settings
# https://docs.djangoproject.com/en/stable/topics/email/

# Use fixed strings in case import paths move
match env.get("EMAIL_BACKEND_NAME", "").upper():
    case "SES":
        EMAIL_BACKEND = "django_ses.SESBackend"
        AWS_SES_REGION_NAME = env["AWS_REGION"]
        USE_SES_V2 = True

    case "SMTP":
        EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
        # https://docs.djangoproject.com/en/stable/ref/settings/#email-host
        if "EMAIL_HOST" in env:
            EMAIL_HOST = env["EMAIL_HOST"]

        # https://docs.djangoproject.com/en/stable/ref/settings/#email-port
        # Use a default port of 587, as Heroku & other services now block the Django default of 25
        try:
            EMAIL_PORT = int(env.get("EMAIL_PORT", 587))
        except ValueError:
            raise ImproperlyConfigured("The setting EMAIL_PORT should be an integer, e.g. 587") from None

        # https://docs.djangoproject.com/en/stable/ref/settings/#email-host-user
        if "EMAIL_HOST_USER" in env:
            EMAIL_HOST_USER = env["EMAIL_HOST_USER"]

        # https://docs.djangoproject.com/en/stable/ref/settings/#email-host-password
        if "EMAIL_HOST_PASSWORD" in env:
            EMAIL_HOST_PASSWORD = env["EMAIL_HOST_PASSWORD"]

        # https://docs.djangoproject.com/en/stable/ref/settings/#email-use-tls
        # We always want to use TLS
        EMAIL_USE_TLS = True

    case _:
        EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"


# https://docs.djangoproject.com/en/stable/ref/settings/#email-subject-prefix
if "EMAIL_SUBJECT_PREFIX" in env:
    EMAIL_SUBJECT_PREFIX = env["EMAIL_SUBJECT_PREFIX"]

# SERVER_EMAIL is used to send emails to administrators.
# https://docs.djangoproject.com/en/stable/ref/settings/#server-email
# DEFAULT_FROM_EMAIL is used as a default for any mail send from the website to
# the users.
# https://docs.djangoproject.com/en/stable/ref/settings/#default-from-email
if "SERVER_EMAIL" in env:
    SERVER_EMAIL = DEFAULT_FROM_EMAIL = env["SERVER_EMAIL"]


# Do not include superusers in all moderation notifications.
WAGTAILADMIN_NOTIFICATION_INCLUDE_SUPERUSERS = False

# Sentry configuration.
is_in_shell = len(sys.argv) > 1 and sys.argv[1] in ["shell", "shell_plus"]

if "SENTRY_DSN" in env and not is_in_shell:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.utils import get_default_release

    sentry_kwargs: dict[str, str | list[Any] | None] = {
        "dsn": env["SENTRY_DSN"],
        "integrations": [DjangoIntegration()],
    }

    # There's a chooser to toggle between environments at the top right corner on sentry.io
    # Values are typically 'staging' or 'production' but can be set to anything else if needed.
    # `heroku config:set SENTRY_ENVIRONMENT=production`
    if sentry_environment := env.get("SENTRY_ENVIRONMENT"):
        sentry_kwargs.update({"environment": sentry_environment})

    release = get_default_release()
    if release is None:
        # Assume this is a Heroku-hosted app with the "runtime-dyno-metadata" lab enabled.
        # see https://devcenter.heroku.com/articles/dyno-metadata
        # `heroku labs:enable runtime-dyno-metadata`
        release = env.get("HEROKU_RELEASE_VERSION", None)

    sentry_kwargs.update({"release": release})
    sentry_sdk.init(**sentry_kwargs)  # type: ignore[arg-type]


# Front-end cache
# This configuration is used to allow purging pages from cache when they are
# published.
# These settings are usually used only on the production sites.
# This is a configuration of the CDN/front-end cache that is used to cache the
# production websites.
# https://docs.wagtail.io/en/latest/reference/contrib/frontendcache.html
# The backend can be configured to use an account-wide API key, or an API token with
# restricted access.

if "FRONTEND_CACHE_CLOUDFLARE_TOKEN" in env or "FRONTEND_CACHE_CLOUDFLARE_BEARER_TOKEN" in env:
    INSTALLED_APPS.append("wagtail.contrib.frontend_cache")
    WAGTAILFRONTENDCACHE = {
        "default": {
            "BACKEND": "wagtail.contrib.frontend_cache.backends.CloudflareBackend",
            "ZONEID": env["FRONTEND_CACHE_CLOUDFLARE_ZONEID"],
        }
    }

    if "FRONTEND_CACHE_CLOUDFLARE_TOKEN" in env:
        # To use an account-wide API key, set the following environment variables:
        #  * FRONTEND_CACHE_CLOUDFLARE_TOKEN
        #  * FRONTEND_CACHE_CLOUDFLARE_EMAIL
        #  * FRONTEND_CACHE_CLOUDFLARE_ZONEID
        # These can be obtained from a sysadmin.
        WAGTAILFRONTENDCACHE["default"].update(
            {
                "EMAIL": env["FRONTEND_CACHE_CLOUDFLARE_EMAIL"],
                "TOKEN": env["FRONTEND_CACHE_CLOUDFLARE_TOKEN"],
            }
        )

    else:
        # To use an API token with restricted access, set the following environment variables:
        #  * FRONTEND_CACHE_CLOUDFLARE_BEARER_TOKEN
        #  * FRONTEND_CACHE_CLOUDFLARE_ZONEID
        WAGTAILFRONTENDCACHE["default"].update({"BEARER_TOKEN": env["FRONTEND_CACHE_CLOUDFLARE_BEARER_TOKEN"]})

    # Set up front-end cache if the S3 uses custom domain. This assumes that
    # the same Cloudflare zone is used.
    if env.get("AWS_S3_CUSTOM_DOMAIN"):
        WAGTAIL_STORAGES_DOCUMENTS_FRONTENDCACHE = WAGTAILFRONTENDCACHE


# Set s-max-age header that is used by reverse proxy/front end cache. See
# urls.py.
try:
    CACHE_CONTROL_S_MAXAGE = int(env.get("CACHE_CONTROL_S_MAXAGE", 600))
except ValueError:
    pass


# Give front-end cache 30 second to revalidate the cache to avoid hitting the
# backend. See urls.py.
CACHE_CONTROL_STALE_WHILE_REVALIDATE = int(env.get("CACHE_CONTROL_STALE_WHILE_REVALIDATE", 30))


# Required to get e.g. wagtail-sharing working on Heroku and probably many other platforms.
# https://docs.djangoproject.com/en/stable/ref/settings/#use-x-forwarded-port
USE_X_FORWARDED_PORT = env.get("USE_X_FORWARDED_PORT", "true").lower().strip() == "true"

XFF_TRUSTED_PROXY_DEPTH = int(env.get("XFF_TRUSTED_PROXY_DEPTH", 1))
XFF_EXEMPT_URLS = [r"^-/.*", r"health"]

# Error if there are the wrong number of proxies
XFF_STRICT = env.get("XFF_STRICT", "false").lower().strip() == "true"

# Security configuration
# This configuration is required to achieve good security rating.
# You can test it using https://securityheaders.com/
# https://docs.djangoproject.com/en/stable/ref/middleware/#module-django.middleware.security

# The Django default for the maximum number of GET or POST parameters is 1000. For
# especially large Wagtail pages with many fields, we need to override this. See
# https://docs.djangoproject.com/en/3.2/ref/settings/#data-upload-max-number-fields
DATA_UPLOAD_MAX_NUMBER_FIELDS = int(env.get("DATA_UPLOAD_MAX_NUMBER_FIELDS", 10_000))

# Enabling this doesn't have any benefits but will make it harder to make
# requests from javascript because the csrf cookie won't be easily accessible.
# https://docs.djangoproject.com/en/stable/ref/settings/#csrf-cookie-httponly
# CSRF_COOKIE_HTTPONLY = True

# Custom view to handle CSRF failures.
CSRF_FAILURE_VIEW = "cms.core.views.csrf_failure"

# Force HTTPS redirect (enabled by default!)
# https://docs.djangoproject.com/en/stable/ref/settings/#secure-ssl-redirect
SECURE_SSL_REDIRECT = env.get("SECURE_SSL_REDIRECT", "true").lower().strip() == "true"


# This will allow the cache to swallow the fact that the website is behind TLS
# and inform the Django using "X-Forwarded-Proto" HTTP header.
# https://docs.djangoproject.com/en/stable/ref/settings/#secure-proxy-ssl-header
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


# This is a setting activating the HSTS header. This will enforce the visitors to use
# HTTPS for an amount of time specified in the header. Since we are expecting our apps
# to run via TLS by default, this header is activated by default.
# The header can be deactivated by setting this setting to 0, as it is done in the
# dev and testing settings.
# https://docs.djangoproject.com/en/stable/ref/settings/#secure-hsts-seconds
DEFAULT_HSTS_SECONDS = 30 * 24 * 60 * 60  # 30 days
SECURE_HSTS_SECONDS = int(env.get("SECURE_HSTS_SECONDS", DEFAULT_HSTS_SECONDS))

# We don't enforce HSTS on subdomains as anything at subdomains is likely outside our control.
# https://docs.djangoproject.com/en/3.2/ref/settings/#secure-hsts-include-subdomains
SECURE_HSTS_INCLUDE_SUBDOMAINS = False


# https://docs.djangoproject.com/en/stable/ref/settings/#secure-content-type-nosniff
SECURE_CONTENT_TYPE_NOSNIFF = True


# https://docs.djangoproject.com/en/stable/ref/middleware/#referrer-policy
SECURE_REFERRER_POLICY = env.get("SECURE_REFERRER_POLICY", "no-referrer-when-downgrade").strip()


# Content Security policy settings
# Most modern browsers don't honor the X-XSS-Protection HTTP header.
# You can use Content-Security-Policy without allowing 'unsafe-inline' scripts instead.
# https://django-csp.readthedocs.io/en/latest/configuration.html
if "CSP_DEFAULT_SRC" in env:
    MIDDLEWARE.append("csp.middleware.CSPMiddleware")

    # The “special” source values of 'self', 'unsafe-inline', 'unsafe-eval', and 'none' must be quoted!
    # e.g.: CSP_DEFAULT_SRC = "'self'" Without quotes they will not work as intended.
    CSP_DEFAULT_SRC = env.get("CSP_DEFAULT_SRC", "").split(",")
    CSP_DIRECTIVES = {
        "default-src": CSP_DEFAULT_SRC,
    }

    if "CSP_SCRIPT_SRC" in env:
        CSP_DIRECTIVES["script-src"] = env.get("CSP_SCRIPT_SRC", "").split(",")
    if "CSP_STYLE_SRC" in env:
        CSP_DIRECTIVES["style-src"] = env.get("CSP_STYLE_SRC", "").split(",")
    if "CSP_IMG_SRC" in env:
        CSP_DIRECTIVES["img-src"] = env.get("CSP_IMG_SRC", "").split(",")
    if "CSP_CONNECT_SRC" in env:
        CSP_DIRECTIVES["connect-src"] = env.get("CSP_CONNECT_SRC", "").split(",")
    if "CSP_FONT_SRC" in env:
        CSP_DIRECTIVES["font-src"] = env.get("CSP_FONT_SRC", "").split(",")
    if "CSP_BASE_URI" in env:
        CSP_DIRECTIVES["base-uri"] = env.get("CSP_BASE_URI", "").split(",")
    if "CSP_OBJECT_SRC" in env:
        CSP_DIRECTIVES["object-src"] = env.get("CSP_OBJECT_SRC", "").split(",")

    if env.get("CSP_REPORT_ONLY", "false").lower() == "true":
        CONTENT_SECURITY_POLICY_REPORT_ONLY = {"DIRECTIVES": CSP_DIRECTIVES}
    else:
        CONTENT_SECURITY_POLICY = {"DIRECTIVES": CSP_DIRECTIVES}


# Basic authentication settings
# These are settings to configure the third-party library:
# https://gitlab.com/tmkn/django-basic-auth-ip-whitelist
if env.get("BASIC_AUTH_ENABLED", "false").lower().strip() == "true":
    # Insert basic auth as a first middleware to be checked first, before
    # anything else.
    MIDDLEWARE.insert(0, "baipw.middleware.BasicAuthIPWhitelistMiddleware")

    # This is the credentials users will have to use to access the site.
    BASIC_AUTH_LOGIN = env.get("BASIC_AUTH_LOGIN", "tbx")
    BASIC_AUTH_PASSWORD = env.get("BASIC_AUTH_PASSWORD", "tbx")

    # Wagtail requires Authorization header to be present for the previews
    BASIC_AUTH_DISABLE_CONSUMING_AUTHORIZATION_HEADER = True

    # This is the list of hosts that website can be accessed without basic auth
    # check. This may be useful to e.g. white-list "llamasavers.com" but not
    # "llamasavers.production.onsdigital.com".
    if "BASIC_AUTH_WHITELISTED_HTTP_HOSTS" in env:
        BASIC_AUTH_WHITELISTED_HTTP_HOSTS = env["BASIC_AUTH_WHITELISTED_HTTP_HOSTS"].split(",")


# Django REST framework settings
# Change default settings that enable basic auth.
REST_FRAMEWORK = {"DEFAULT_AUTHENTICATION_CLASSES": ("rest_framework.authentication.SessionAuthentication",)}


AUTH_USER_MODEL = "users.User"

# django-defender
# Records failed login attempts and blocks access by username and IP
# https://django-defender.readthedocs.io/en/latest/
ENABLE_DJANGO_DEFENDER = (
    "redis" in CACHES["default"]["BACKEND"].lower()
    and env.get("ENABLE_DJANGO_DEFENDER", "True").lower().strip() == "true"
)

if ENABLE_DJANGO_DEFENDER:
    INSTALLED_APPS += ["defender"]
    MIDDLEWARE.append("defender.middleware.FailedLoginMiddleware")

    # See https://django-defender.readthedocs.io/en/latest/#customizing-django-defender
    # Use same Redis client as cache
    DEFENDER_REDIS_NAME = "default"
    DEFENDER_LOGIN_FAILURE_LIMIT_IP = 20
    DEFENDER_LOGIN_FAILURE_LIMIT_USERNAME = 5
    DEFENDER_COOLOFF_TIME = int(env.get("DJANGO_DEFENDER_COOLOFF_TIME", 600))  # default to 10 minutes
    DEFENDER_LOCKOUT_TEMPLATE = "pages/defender/lockout.html"

    # Whilst we frequently are behind a reverse proxy, using `False` ensures Defender falls
    # back to using `REMOTE_ADDR`, which is set correctly by `django-xff`.
    DEFENDER_BEHIND_REVERSE_PROXY = False


# Wagtail settings


# This name is displayed in the Wagtail admin.
WAGTAIL_SITE_NAME = "Office for National Statistics"

# Enforce non-trailing slash URLs
APPEND_SLASH = False
WAGTAIL_APPEND_SLASH = False

# Base URL to use when formatting absolute URLs within the Wagtail admin in
# contexts without a request, e.g. in notification emails. Don't include '/admin'
# or a trailing slash.
if "WAGTAILADMIN_BASE_URL" in env:
    WAGTAILADMIN_BASE_URL = env["WAGTAILADMIN_BASE_URL"]

# https://docs.wagtail.org/en/latest/reference/settings.html#wagtailadmin-login-url
WAGTAILADMIN_LOGIN_URL = env.get("WAGTAILADMIN_LOGIN_URL", "/admin/login/")

# Custom image model
# https://docs.wagtail.io/en/stable/advanced_topics/images/custom_image_model.html
WAGTAILIMAGES_IMAGE_MODEL = "images.CustomImage"
WAGTAILIMAGES_FEATURE_DETECTION_ENABLED = False

pixel_limit = env.get("WAGTAILIMAGES_MAX_IMAGE_PIXELS")
WAGTAILIMAGES_MAX_IMAGE_PIXELS = int(pixel_limit) if pixel_limit else 10_000_000

# Rich text settings to remove unneeded features
# We normally don't want editors to use the images
# in the rich text editor, for example.
# They should use the image stream block instead
RICH_TEXT_BASIC = ["bold", "italic", "link", "ol", "ul"]
RICH_TEXT_FULL = ["h3", "h4", *RICH_TEXT_BASIC, "document-link"]

WAGTAILADMIN_RICH_TEXT_EDITORS = {
    "default": {
        "WIDGET": "wagtail.admin.rich_text.DraftailRichTextArea",
        "OPTIONS": {"features": RICH_TEXT_FULL},
    }
}

# Custom document model
# https://docs.wagtail.io/en/stable/advanced_topics/documents/custom_document_model.html
WAGTAILDOCS_DOCUMENT_MODEL = "documents.CustomDocument"


# Document serve method - avoid serving files directly from the storage.
# https://docs.wagtail.io/en/stable/advanced_topics/settings.html#documents
WAGTAILDOCS_SERVE_METHOD = "serve_view"


WAGTAIL_FRONTEND_LOGIN_TEMPLATE = "templates/pages/login_page.html"  # pragma: allowlist secret
# pragma: allowlist nextline secret
WAGTAIL_PASSWORD_REQUIRED_TEMPLATE = "templates/pages/wagtail/password_required.html"  # noqa: S105


# Default size of the pagination used on the front-end.
DEFAULT_PER_PAGE = 20
PREVIOUS_RELEASES_PER_PAGE = int(env.get("PREVIOUS_RELEASES_PER_PAGE", 10))
RELATED_DATASETS_PER_PAGE = int(env.get("RELATED_DATASETS_PER_PAGE", DEFAULT_PER_PAGE))

# Google Tag Manager ID from env
GOOGLE_TAG_MANAGER_CONTAINER_ID = env.get("GOOGLE_TAG_MANAGER_CONTAINER_ID", "")

# Allows us to toggle search indexing via an environment variable.
SEO_NOINDEX = env.get("SEO_NOINDEX", "false").lower() == "true"

TESTING = "test" in sys.argv

# By default, Django uses a computationally difficult algorithm for passwords hashing.
# We don't need such a strong algorithm in tests, so use MD5
if TESTING:
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


# Disable new version check and "what's new" banner
WAGTAIL_ENABLE_UPDATE_CHECK = False
WAGTAIL_ENABLE_WHATS_NEW_BANNER = False


# Isolates the browsing context exclusively to same-origin documents.
# Cross-origin documents are not loaded in the same browsing context.
# Set to "same-origin-allow-popups" to allow popups
# from third-party applications like PayPal or Zoom as needed
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"

#
# ONS CMS specific-settings
#

# See
# https://docs.djangoproject.com/en/5.1/topics/i18n/formatting/#creating-custom-format-files
FORMAT_MODULE_PATH = ["cms.settings.formats"]

# Default date formats. Also overridden in cms.settings.formats.en_GB.formats
# as the locale-based formats take precedence to the global ones, and we use the en-gb locale.
DATE_FORMAT = "j F Y"
DATETIME_FORMAT = "j F Y g:ia"  # 1 November 2024, 1 p.m.

# ONS Cookie banner settings
ONS_COOKIE_BANNER_SERVICE_NAME = env.get("ONS_COOKIE_BANNER_SERVICE_NAME", "ons.gov.uk")
ONS_COOKIES_PAGE_SLUG = "cookies"

# Project information
BUILD_TIME = datetime.datetime.fromtimestamp(int(env["BUILD_TIME"])) if env.get("BUILD_TIME") else None
GIT_COMMIT = env.get("GIT_COMMIT") or None
TAG = env.get("TAG") or None
START_TIME = datetime.datetime.now(tz=datetime.UTC)

SLACK_NOTIFICATIONS_WEBHOOK_URL = env.get("SLACK_NOTIFICATIONS_WEBHOOK_URL")

# API bases
ONS_API_BASE_URL = env.get("ONS_API_BASE_URL", "https://api.beta.ons.gov.uk/v1")
DATASETS_API_BASE_URL = env.get("DATASETS_API_BASE_URL", f"{ONS_API_BASE_URL}/datasets")  # used for dataset choosers
DATASETS_API_EDITIONS_URL = env.get("DATASETS_API_EDITIONS_URL", f"{ONS_API_BASE_URL}/dataset-editions")
DIS_DATASETS_BUNDLE_API_BASE_URL = env.get("DIS_DATASETS_BUNDLE_API_BASE_URL", ONS_API_BASE_URL)
TOPIC_API_BASE_URL = env.get("TOPIC_API_BASE_URL", f"{ONS_API_BASE_URL}/topics")  # used to sync topics

# Feature flag to enable/disable interaction with the ONS Bundle API
DIS_DATASETS_BUNDLE_API_ENABLED = env.get("DIS_DATASETS_BUNDLE_API_ENABLED", "false").lower() == "true"

# Feature flag to enable/disable validation of bundled datasets status on bundle approval
BUNDLE_DATASET_STATUS_VALIDATION_ENABLED = (
    env.get("BUNDLE_DATASET_STATUS_VALIDATION_ENABLED", "false").lower() == "true"
)

ONS_WEBSITE_BASE_URL = env.get("ONS_WEBSITE_BASE_URL", "https://www.ons.gov.uk")
ONS_ORGANISATION_NAME = env.get("ONS_ORGANISATION_NAME", "Office for National Statistics")

DEFAULT_OG_IMAGE_URL = env.get("DEFAULT_OG_IMAGE_URL", "https://cdn.ons.gov.uk/assets/images/ons-logo/v2/ons-logo.png")

WAGTAILSIMPLETRANSLATION_SYNC_PAGE_TREE = True

# Configuration for the External Search service
SEARCH_INDEX_PUBLISHER_BACKEND = os.getenv("SEARCH_INDEX_PUBLISHER_BACKEND")
KAFKA_SERVERS = os.getenv("KAFKA_SERVERS", "").split(",")
KAFKA_USE_IAM_AUTH = os.getenv("KAFKA_USE_IAM_AUTH", "false").lower() == "true"

SEARCH_INDEX_EXCLUDED_PAGE_TYPES = {
    "HomePage",
    "ArticlesIndexPage",
    "ArticleSeriesPage",
    "MethodologyIndexPage",
    "ReleaseCalendarIndex",
    "ThemeIndexPage",
    "ThemePage",
    "TopicPage",
    "CookiesPage",
    "Page",
}

# Allow-list of language codes whose pages are included in search indexing
SEARCH_INDEX_INCLUDED_LANGUAGES = env.get("SEARCH_INDEX_INCLUDED_LANGUAGES", LANGUAGE_CODE).split(",")

# Allowed domains for linking to other parts of the ONS website (for datasets or time series)
ONS_ALLOWED_LINK_DOMAINS = env.get("ONS_ALLOWED_LINK_DOMAINS", "ons.gov.uk").split(",")

# Allowed prefixes for iframe visualisations
if "IFRAME_VISUALISATION_ALLOWED_DOMAINS" in env:
    IFRAME_VISUALISATION_ALLOWED_DOMAINS = env["IFRAME_VISUALISATION_ALLOWED_DOMAINS"].split(",")
else:  # Default to ONS allowed link domains if not set
    IFRAME_VISUALISATION_ALLOWED_DOMAINS = ONS_ALLOWED_LINK_DOMAINS


# Allowed path prefixes for iframe visualisations
IFRAME_VISUALISATION_PATH_PREFIXES = env.get(
    "IFRAME_VISUALISATION_PATH_PREFIXES",
    "/visualisations",
).split(",")

# FIXME: remove before going live
ENFORCE_EXCLUSIVE_TAXONOMY = env.get("ENFORCE_EXCLUSIVE_TAXONOMY", "true").lower() == "true"
ALLOW_TEAM_MANAGEMENT = env.get("ALLOW_TEAM_MANAGEMENT", "false").lower() == "true"

SEARCH_API_DEFAULT_PAGE_SIZE = int(os.getenv("SEARCH_API_DEFAULT_PAGE_SIZE", "20"))
SEARCH_API_MAX_PAGE_SIZE = int(os.getenv("SEARCH_API_MAX_PAGE_SIZE", "500"))

# Auth
SERVICE_AUTH_TOKEN = env.get("SERVICE_AUTH_TOKEN")
WAGTAIL_CORE_ADMIN_LOGIN_ENABLED = env.get("WAGTAIL_CORE_ADMIN_LOGIN_ENABLED", "false").lower() == "true"
LOGOUT_REDIRECT_URL = env.get("LOGOUT_REDIRECT_URL", WAGTAILADMIN_LOGIN_URL)
AUTH_TOKEN_REFRESH_URL = env.get("AUTH_TOKEN_REFRESH_URL")
SESSION_COOKIE_AGE = int(env.get("SESSION_COOKIE_AGE", 60 * 15))  # 15 minutes to match Auth Service
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
IDENTITY_API_BASE_URL = env.get("IDENTITY_API_BASE_URL")
AWS_COGNITO_LOGIN_ENABLED = env.get("AWS_COGNITO_LOGIN_ENABLED", "false").lower() == "true"
AWS_COGNITO_USER_POOL_ID = env.get("AWS_COGNITO_USER_POOL_ID")
AWS_COGNITO_APP_CLIENT_ID = env.get("AWS_COGNITO_APP_CLIENT_ID")

# Auth Sync Teams
AWS_COGNITO_TEAM_SYNC_ENABLED = env.get("AWS_COGNITO_TEAM_SYNC_ENABLED", "false").lower() == "true"
AWS_COGNITO_TEAM_SYNC_FREQUENCY = int(env.get("AWS_COGNITO_TEAM_SYNC_FREQUENCY", "1"))

# Groups
PUBLISHING_ADMIN_GROUP_NAME = "Publishing Admins"
PUBLISHING_OFFICER_GROUP_NAME = "Publishing Officers"
VIEWERS_GROUP_NAME = "Viewers"
ROLE_GROUP_IDS = {"role-admin", "role-publisher"}

# Cookie Names
ACCESS_TOKEN_COOKIE_NAME = "access_token"  # noqa: S105
REFRESH_TOKEN_COOKIE_NAME = "refresh_token"  # noqa: S105
ID_TOKEN_COOKIE_NAME = "id_token"  # noqa: S105

WAGTAILADMIN_HOME_PATH = env.get("WAGTAILADMIN_HOME_PATH", "admin/")
DJANGO_ADMIN_HOME_PATH = env.get("DJANGO_ADMIN_HOME_PATH", "django-admin/")
SESSION_RENEWAL_OFFSET_SECONDS = env.get("SESSION_RENEWAL_OFFSET_SECONDS", 60 * 5)  # 5 minutes

# Contact Us URL for error pages
CONTACT_US_URL = env.get("CONTACT_US_URL", "/aboutus/contactus/generalandstatisticalenquiries")

# Backup site URL
BACKUP_SITE_URL = env.get("BACKUP_SITE_URL", "https://backup.ons.gov.uk")

CMS_RESOURCES_ENDPOINT_ENABLED = env.get("CMS_RESOURCES_ENDPOINT_ENABLED", "false").lower() == "true"

USE_I18N_ROOT_NO_TRAILING_SLASH = env.get("USE_I18N_ROOT_NO_TRAILING_SLASH", "false").lower() == "true"

# Allow to override but default to enabled
CMS_SEARCH_NOTIFY_ON_DELETE_OR_UNPUBLISH = env.get("CMS_SEARCH_NOTIFY_ON_DELETE_OR_UNPUBLISH", "true").lower() == "true"

# Domain-based locale configuration
CMS_USE_SUBDOMAIN_LOCALES = env.get("CMS_USE_SUBDOMAIN_LOCALES", "true").lower() == "true"

# This must remain lower than the Gunicorn worker timeout.
# Note, the Gunicorn timeout may itself be overridden in deployment config (e.g. gunicorn.conf.py, Helm chart values).
HTTP_REQUEST_DEFAULT_TIMEOUT_SECONDS = int(env.get("HTTP_REQUEST_DEFAULT_TIMEOUT_SECONDS", 10))

DATASETS_API_DEFAULT_PAGE_SIZE = int(env.get("DATASETS_API_DEFAULT_PAGE_SIZE", "100"))
