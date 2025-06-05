from .base import MIDDLEWARE  # Explicitly import MIDDLEWARE to avoid undefined errors
from .test import *  # noqa: F403  # pylint: disable=wildcard-import,unused-wildcard-import

REDIS_URL = "redis://localhost:16379"

DATABASES["default"]["PORT"] = DATABASES["read_replica"]["PORT"] = 15432  # noqa: F405

# strip out our custom ONSAuthMiddleware
# In our functional tests we need to bypass the Cognito/ JWT checks while still exercising
# the “Cognito is enabled” code paths (e.g. injecting <script id="auth-config"> and hitting
# /admin/extend-session/). Stripping out just the middleware lets us keep AWS_COGNITO_LOGIN_ENABLED=True
# so that templates and views behave as if Cognito is live, but prevents ONSAuthMiddleware from
# rejecting our fake JWT or logging out the test user.

# Remove ONSAuthMiddleware so that fake/ minimal JWT tokens injected by auth.js aren't validated
# otherwise, every request would hit validate_jwt(), see an invalid/ unsigned token, and immediately log out.
MIDDLEWARE = [mw for mw in MIDDLEWARE if mw != "cms.auth.middleware.ONSAuthMiddleware"]

# ensure Django's AuthenticationMiddleware is present (just after SessionMiddleware)
# ONSAuthMiddleware inherited from AuthenticationMiddleware, so removing it also removed Django's
# session-based authentication step. We need plain AuthenticationMiddleware to populate request.user
# from the session cookie after “superuser logs in” in our tests. Ensure it's inserted right after
# SessionMiddleware so request.user is set correctly.
if "django.contrib.auth.middleware.AuthenticationMiddleware" not in MIDDLEWARE:
    idx = MIDDLEWARE.index("django.contrib.sessions.middleware.SessionMiddleware")
    MIDDLEWARE.insert(
        idx + 1,
        "django.contrib.auth.middleware.AuthenticationMiddleware",
    )
