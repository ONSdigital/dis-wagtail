from __future__ import annotations  # needed for unquoted forward references because of Django Views

from typing import TYPE_CHECKING, ClassVar

from django.db.models import QuerySet
from django.utils.functional import cached_property

from .enums import ACTIVE_BUNDLE_STATUSES
from .panels import BundleNotePanel

if TYPE_CHECKING:
    from wagtail.admin.panels import Panel

    from .models import Bundle


class BundledPageMixin:
    """A helper page mixin for bundled content.

    Add it to Page classes that should be in bundles.
    """

    panels: ClassVar[list[Panel]] = [BundleNotePanel(heading="Bundle", icon="boxes-stacked")]

    @cached_property
    def bundles(self) -> QuerySet[Bundle]:
        """Return all bundles this instance belongs to."""
        # Avoid circular import
        from cms.bundles.models import Bundle  # pylint: disable=import-outside-toplevel

        queryset: QuerySet[Bundle] = Bundle.objects.none()
        if self.pk:  # type: ignore[attr-defined]
            queryset = Bundle.objects.filter(
                pk__in=self.bundlepage_set.all().values_list("parent", flat=True)  # type: ignore[attr-defined]
            )
        return queryset

    @cached_property
    def active_bundles(self) -> QuerySet[Bundle]:
        """Returns the active bundles this instance belongs to. In theory, it should be only one."""
        return self.bundles.filter(status__in=ACTIVE_BUNDLE_STATUSES)

    @cached_property
    def active_bundle(self) -> Bundle | None:
        return self.active_bundles.first()

    @cached_property
    def in_active_bundle(self) -> bool:
        return self.active_bundle is not None
