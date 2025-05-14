from functools import cache

from wagtail.coreutils import resolve_model_string
from wagtail.models import Page, get_page_models

from cms.bundles.enums import ACTIVE_BUNDLE_STATUSES


@cache
def get_bundleable_page_types() -> list[type[Page]]:
    # using this rather than inline import to placate pyright complaining about cyclic imports
    module = __import__("cms.bundles.models", fromlist=["BundledPageMixin"])
    bundle_page_mixin_class = module.BundledPageMixin

    return [model for model in get_page_models() if issubclass(model, bundle_page_mixin_class)]


def get_pages_in_active_bundles() -> list[int]:
    # using this rather than inline import to placate pyright complaining about cyclic imports
    bundle_page_class = resolve_model_string("bundles.BundlePage")

    return list(
        bundle_page_class.objects.filter(parent__status__in=ACTIVE_BUNDLE_STATUSES).values_list("page", flat=True)
    )
