from typing import TYPE_CHECKING, Any, ClassVar, Optional, Self

from django.db import models
from django.db.models import F, QuerySet
from django.db.models.functions import Coalesce
from django.utils.functional import cached_property
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, FieldRowPanel, InlinePanel
from wagtail.models import Orderable, Page
from wagtail.search import index

from .enums import ACTIVE_BUNDLE_STATUSES, EDITABLE_BUNDLE_STATUSES, BundleStatus
from .forms import BundleAdminForm
from .panels import BundleNotePanel, PageChooserWithStatusPanel

if TYPE_CHECKING:
    import datetime

    from wagtail.admin.panels import Panel


class BundlePage(Orderable):
    parent = ParentalKey("Bundle", related_name="bundled_pages", on_delete=models.CASCADE)
    page = models.ForeignKey(  # type: ignore[var-annotated]
        "wagtailcore.Page", blank=True, null=True, on_delete=models.SET_NULL
    )

    panels: ClassVar[list["Panel"]] = [
        PageChooserWithStatusPanel("page", ["analysis.AnalysisPage"]),
    ]

    def __str__(self) -> str:
        return f"BundlePage: page {self.page_id} in bundle {self.parent_id}"


class BundlesQuerySet(QuerySet):
    def active(self) -> Self:
        """Provides a pre-filtered queryset for active bundles. Usage: Bundle.objects.active()."""
        return self.filter(status__in=ACTIVE_BUNDLE_STATUSES)

    def editable(self) -> Self:
        """Provides a pre-filtered queryset for editable bundles. Usage: Bundle.objects.editable()."""
        return self.filter(status__in=EDITABLE_BUNDLE_STATUSES)


# note: mypy doesn't cope with dynamic base classes and fails with:
# 'Unsupported dynamic base class "models.Manager.from_queryset"  [misc]'
# @see https://github.com/python/mypy/issues/2477
class BundleManager(models.Manager.from_queryset(BundlesQuerySet)):  # type: ignore[misc]
    def get_queryset(self) -> BundlesQuerySet:
        """Augments the queryset to order it by the publication date, then name, then reverse id."""
        queryset: BundlesQuerySet = super().get_queryset()
        queryset = queryset.alias(
            release_date=Coalesce("publication_date", "release_calendar_page__release_date")
        ).order_by(F("release_date").desc(nulls_last=True), "name", "-pk")
        return queryset  # note: not returning directly to placate no-any-return


class Bundle(index.Indexed, ClusterableModel, models.Model):  # type: ignore[django-manager-missing]
    base_form_class = BundleAdminForm

    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="bundles",
    )
    # See https://docs.wagtail.org/en/stable/advanced_topics/reference_index.html
    created_by.wagtail_reference_index_ignore = True  # type: ignore[attr-defined]

    approved_at = models.DateTimeField(blank=True, null=True)
    approved_by = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_bundles",
    )
    approved_by.wagtail_reference_index_ignore = True  # type: ignore[attr-defined]

    publication_date = models.DateTimeField(blank=True, null=True)
    release_calendar_page = models.ForeignKey(
        "release_calendar.ReleaseCalendarPage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="bundles",
    )
    status = models.CharField(choices=BundleStatus.choices, default=BundleStatus.PENDING, max_length=32)

    objects = BundleManager()

    panels: ClassVar[list["Panel"]] = [
        FieldPanel("name"),
        FieldRowPanel(
            [
                FieldPanel("release_calendar_page", heading="Release Calendar page"),
                FieldPanel("publication_date", heading="or Publication date"),
            ],
            heading=_("Scheduling"),
            icon="calendar",
        ),
        FieldPanel("status"),
        InlinePanel("bundled_pages", heading=_("Bundled pages"), icon="doc-empty", label=_("Page")),
        # these are handled by the form
        FieldPanel("approved_by", classname="hidden w-hidden"),
        FieldPanel("approved_at", classname="hidden w-hidden"),
    ]

    search_fields: ClassVar[list[index.SearchField | index.AutocompleteField]] = [
        index.SearchField("name"),
        index.AutocompleteField("name"),
    ]

    def __str__(self) -> str:
        return str(self.name)

    @cached_property
    def scheduled_publication_date(self) -> Optional["datetime.datetime"]:
        """Returns the direct publication date or the linked release calendar page, if set."""
        date: datetime.datetime | None = self.publication_date
        if not date and self.release_calendar_page_id:
            date = self.release_calendar_page.release_date  # type: ignore[union-attr]
        return date

    @property
    def can_be_approved(self) -> bool:
        """Determines whether the bundle can be approved (i.e. is not already approved or released).

        Note: strictly speaking, the bundle should be in "in review" in order for it to be approved.
        """
        return self.status in [BundleStatus.PENDING, BundleStatus.IN_REVIEW]

    def get_bundled_pages(self) -> QuerySet[Page]:
        pages: QuerySet[Page] = Page.objects.filter(pk__in=self.bundled_pages.values_list("page__pk", flat=True))
        return pages

    def save(self, **kwargs: Any) -> None:  # type: ignore[override]
        """Adds additional behaviour on bundle saving.

        For non-released bundles, we update the publication date for related pages if needed.
        """
        super().save(**kwargs)

        if self.status == BundleStatus.RELEASED:
            return

        if self.scheduled_publication_date and self.scheduled_publication_date >= now():
            # Schedule publishing for related pages.
            # ignoring [attr-defined] because Wagtail is not fully typed and mypy is confused.
            for bundled_page in self.get_bundled_pages().defer_streamfields().specific():  # type: ignore[attr-defined]
                if bundled_page.go_live_at == self.scheduled_publication_date:
                    continue

                # note: this could use a custom log action for history
                bundled_page.go_live_at = self.scheduled_publication_date
                revision = bundled_page.save_revision()
                revision.publish()


class BundledPageMixin:
    """A helper page mixin for bundled content.

    Add it to Page classes that should be in bundles.
    """

    panels: ClassVar[list["Panel"]] = [BundleNotePanel(heading="Bundle", icon="boxes-stacked")]

    @cached_property
    def bundles(self) -> QuerySet[Bundle]:
        """Return all bundles this instance belongs to."""
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