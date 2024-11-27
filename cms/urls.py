from typing import TYPE_CHECKING, Union

from django.apps import apps
from django.conf import settings
from django.urls import include, path
from django.views.decorators.cache import never_cache
from django.views.decorators.vary import vary_on_headers
from django.views.generic import TemplateView
from wagtail import urls as wagtail_urls
from wagtail.contrib.sitemaps.views import sitemap
from wagtail.documents import urls as wagtaildocs_urls
from wagtail.utils.urlpatterns import decorate_urlpatterns

from cms.core import views as core_views
from cms.core.cache import get_default_cache_control_decorator

if TYPE_CHECKING:
    from django.urls import URLPattern, URLResolver

# Internal URLs are not intended for public use.
internal_urlpatterns = [path("readiness/", core_views.ready, name="readiness")]

# Private URLs are not meant to be cached.
private_urlpatterns = [
    path("documents/", include(wagtaildocs_urls)),
    path("-/", include((internal_urlpatterns, "internal"))),
]

# `wagtail.admin` must always be installed,
# so check `IS_EXTERNAL_ENV` directly.
if not settings.IS_EXTERNAL_ENV:
    from wagtail.admin import urls as wagtailadmin_urls  # pylint: disable=ungrouped-imports

    private_urlpatterns.append(path("admin/", include(wagtailadmin_urls)))

if apps.is_installed("django.contrib.admin"):
    from django.contrib import admin  # pylint: disable=ungrouped-imports

    private_urlpatterns.append(path("django-admin/", admin.site.urls))

# django-defender
if getattr(settings, "ENABLE_DJANGO_DEFENDER", False):
    private_urlpatterns += [
        path("django-admin/defender/", include("defender.urls")),
    ]


debug_urlpatterns: list[Union["URLResolver", "URLPattern"]] = []

if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    # Serve static and media files from development server
    debug_urlpatterns += staticfiles_urlpatterns()
    debug_urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    debug_urlpatterns += [
        # Add views for testing 404 and 500 templates
        path(
            "test404/",
            TemplateView.as_view(template_name="templates/pages/errors/404.html"),
        ),
        path(
            "test403/",
            TemplateView.as_view(template_name="templates/pages/errors/403.html"),
        ),
        path(
            "test500/",
            TemplateView.as_view(template_name="templates/pages/errors/500.html"),
        ),
    ]

    # Try to install the django debug toolbar, if exists
    if apps.is_installed("debug_toolbar"):
        import debug_toolbar

        debug_urlpatterns = [path("__debug__/", include(debug_toolbar.urls)), *debug_urlpatterns]

# Public URLs that are meant to be cached.
urlpatterns = [
    path("sitemap.xml", sitemap),
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

# Join private and public URLs.
urlpatterns = (
    private_urlpatterns
    + debug_urlpatterns
    + urlpatterns
    + [
        # Add Wagtail URLs at the end.
        # Wagtail cache-control is set on the page models' serve methods
        path("", include(wagtail_urls)),
    ]
)

# Error handlers
handler404 = "cms.core.views.page_not_found"
handler500 = "cms.core.views.server_error"
# CSRF errors also have their own views - see the `CSRF_FAILURE_VIEW` Django setting
