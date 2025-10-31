from django.apps import apps
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.urls import URLPattern, URLResolver, include, path, re_path
from django.views.decorators.cache import never_cache
from django.views.decorators.vary import vary_on_headers
from django.views.generic import RedirectView, TemplateView
from wagtail import urls as wagtail_urls
from wagtail.documents.views.serve import authenticate_with_password
from wagtail.utils.urlpatterns import decorate_urlpatterns

from cms.auth.views import ONSLogoutView, extend_session
from cms.core import views as core_views
from cms.core.cache import get_default_cache_control_decorator
from cms.home.views import serve_localized_homepage
from cms.private_media import views as private_media_views

# Internal URLs are not intended for public use.
internal_urlpatterns = [
    path("readiness", core_views.ready, name="readiness"),
    path("liveness", core_views.liveness, name="liveness"),
    path("health", core_views.health, name="health"),
]

# Private URLs are not meant to be cached.
# The internal and health paths are also bypassed in authentication middleware in cms/auth/middleware.py.
private_urlpatterns = [
    path("-/", include((internal_urlpatterns, "internal"))),
    path("health", core_views.health, name="health"),
    path(
        "documents/authenticate_with_password/<int:restriction_id>",
        authenticate_with_password,
        name="wagtaildocs_authenticate_with_password",
    ),
]

# `wagtail.admin` must always be installed,
# so check `IS_EXTERNAL_ENV` directly.
if not settings.IS_EXTERNAL_ENV:
    from wagtail.admin import urls as wagtailadmin_urls  # pylint: disable=ungrouped-imports

    # Conditionally include Wagtail admin URLs
    wagtail_admin_patterns = [
        path(
            "logout/",
            ONSLogoutView.as_view(),
            name="wagtailadmin_logout",
        ),
        path("extend-session/", extend_session, name="extend_session"),
    ]
    if not settings.WAGTAIL_CORE_ADMIN_LOGIN_ENABLED:
        # Filter wagtail admin patterns to exclude /login and /password_reset
        wagtail_admin_patterns += [
            path(
                "login/",
                RedirectView.as_view(url=settings.WAGTAILADMIN_LOGIN_URL, permanent=False),
                name="wagtailadmin_login",
            ),
            path(
                "password_reset/",
                RedirectView.as_view(url=settings.WAGTAILADMIN_LOGIN_URL, permanent=False),
                name="wagtailadmin_password_reset",
            ),
        ]

    wagtail_admin_patterns += wagtailadmin_urls.urlpatterns
    private_urlpatterns.append(path(settings.WAGTAILADMIN_HOME_PATH, include(wagtail_admin_patterns)))

if apps.is_installed("django.contrib.admin") and settings.WAGTAIL_CORE_ADMIN_LOGIN_ENABLED:
    from django.contrib import admin  # pylint: disable=ungrouped-imports

    private_urlpatterns.append(path(settings.DJANGO_ADMIN_HOME_PATH, admin.site.urls))

# django-defender
if getattr(settings, "ENABLE_DJANGO_DEFENDER", False):
    private_urlpatterns += [
        path(f"{settings.DJANGO_ADMIN_HOME_PATH}/defender/", include("defender.urls")),
    ]


debug_urlpatterns: list[URLResolver | URLPattern] = []

if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    # Serve static and media files from development server
    debug_urlpatterns += staticfiles_urlpatterns()
    debug_urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    debug_urlpatterns += [
        # Add views for testing 404 and 500 templates
        path(
            "test404",
            TemplateView.as_view(template_name="templates/pages/errors/404.html"),
        ),
        path(
            "test403",
            TemplateView.as_view(template_name="templates/pages/errors/403.html"),
        ),
        path(
            "test500",
            TemplateView.as_view(template_name="templates/pages/errors/500.html"),
        ),
    ]

    # Try to install the django debug toolbar, if exists
    if apps.is_installed("debug_toolbar"):
        import debug_toolbar

        debug_urlpatterns = [path("__debug__/", include(debug_toolbar.urls)), *debug_urlpatterns]

# Public URLs that are meant to be cached.
urlpatterns: list[URLResolver | URLPattern] = []

if settings.IS_EXTERNAL_ENV:
    urlpatterns += [
        path("", include("cms.search.urls")),
    ]
else:
    private_urlpatterns += [
        path("", include("cms.search.urls")),
    ]

# Set public URLs to use the "default" cache settings.
urlpatterns = decorate_urlpatterns(urlpatterns, get_default_cache_control_decorator())

# Set private URLs to use the "never cache" cache settings.
private_urlpatterns = decorate_urlpatterns(private_urlpatterns, never_cache)

# Set vary header to instruct cache to serve different version on different
# cookies, different request method (e.g. AJAX) and different protocol
# (http vs https).
urlpatterns = decorate_urlpatterns(
    urlpatterns,
    vary_on_headers("Cookie", "X-Requested-With", "X-Forwarded-Proto", "Accept-Encoding"),
)

localized_homepage_urlpatterns = []

# Add localized homepage patterns for non-default languages at the root level.
# This is to deal with the fact that i18n_patterns will create URLs like /cy/ instead of /cy.
non_default_languages = [lang[0] for lang in settings.LANGUAGES if lang[0] != settings.LANGUAGE_CODE]
LANGUAGE_CODES_PATTERN = "|".join(non_default_languages)  # e.g., 'cy|uk'

if LANGUAGE_CODES_PATTERN:
    localized_homepage_urlpatterns = [
        re_path(
            rf"^(?P<lang_code>{LANGUAGE_CODES_PATTERN})$",
            serve_localized_homepage,
            name="localized_homepage",
        )
    ]

# Join private and public URLs.
urlpatterns = (
    private_urlpatterns
    + debug_urlpatterns
    + urlpatterns
    + localized_homepage_urlpatterns
    + [
        re_path(
            r"^documents/(\d+)/(.*)$",
            private_media_views.DocumentServeView.as_view(),
            name="wagtaildocs_serve",
        ),
        re_path(
            r"^images/([^/]*)/(\d*)/([^/]*)/[^/]*$",
            private_media_views.ImageServeView.as_view(),
            name="wagtailimages_serve",
        ),
    ]
)

if settings.CMS_USE_SUBDOMAIN_LOCALES:
    urlpatterns += [path("", include(wagtail_urls))]
else:
    urlpatterns += i18n_patterns(
        path("", include(wagtail_urls)),
        prefix_default_language=False,
    )

# Error handlers
handler404 = "cms.core.views.page_not_found"
handler500 = "cms.core.views.server_error"
# CSRF errors also have their own views - see the `CSRF_FAILURE_VIEW` Django setting
