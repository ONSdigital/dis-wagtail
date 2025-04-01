from functools import cache

from wagtail.models import Page, get_page_models

from cms.bundles.enums import ACTIVE_BUNDLE_STATUSES


@cache
def get_bundleable_page_types() -> list[type[Page]]:
    # imported inline to avoid partial-loaded module error
    from cms.bundles.models import BundledPageMixin  # pylint: disable=import-outside-toplevel

    return [model for model in get_page_models() if issubclass(model, BundledPageMixin)]


def get_pages_in_active_bundles() -> list[int]:
    # imported inline to avoid partial-loaded module error
    from cms.bundles.models import BundlePage  # pylint: disable=import-outside-toplevel

    return list(BundlePage.objects.filter(parent__status__in=ACTIVE_BUNDLE_STATUSES).values_list("page", flat=True))
