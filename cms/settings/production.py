# Most of the settings are set in base.py, that's why this file appears fairly
# empty.
from .base import *  # noqa: F403 # pylint: disable=wildcard-import,unused-wildcard-import

# Explicitly disable debug mode in production
DEBUG = False

# Security configuration

# Ensure that the session cookie is only sent by browsers under an HTTPS connection.
# https://docs.djangoproject.com/en/stable/ref/settings/#session-cookie-secure
SESSION_COOKIE_SECURE = True

# Ensure that the CSRF cookie is only sent by browsers under an HTTPS connection.
# https://docs.djangoproject.com/en/stable/ref/settings/#csrf-cookie-secure
CSRF_COOKIE_SECURE = True

# Allow the redirect importer to work in load-balanced / cloud environments.
# https://docs.wagtail.org/en/v6.2.2/reference/settings.html#redirects
WAGTAIL_REDIRECTS_FILE_STORAGE = "cache"
