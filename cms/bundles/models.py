from typing import TYPE_CHECKING, ClassVar, Optional, Self

from django.db import models
from django.db.models import F, QuerySet
from django.db.models.functions import Coalesce
from django.utils.functional import cached_property
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, FieldRowPanel, InlinePanel, MultipleChooserPanel
from wagtail.models import Orderable, Page
from wagtail.search import index

from cms.core.widgets import datetime_widget
from cms.home.models import HomePage
from cms.release_calendar.viewsets import FutureReleaseCalendarChooserWidget
from cms.topics.models import TopicPage
from cms.workflows.utils import is_page_ready_to_preview, is_page_ready_to_publish

from .enums import ACTIVE_BUNDLE_STATUSES, EDITABLE_BUNDLE_STATUSES, PREVIEWABLE_BUNDLE_STATUSES, BundleStatus
from .forms import BundleAdminForm
from .panels import PageChooserWithStatusPanel

if TYPE_CHECKING:
    import datetime

    from wagtail.admin.panels import Panel
    from wagtail.query import PageQuerySet

    from cms.teams.models import Team

PREVIEWER_EXCLUDED_PAGE_TYPES = (HomePage, TopicPage)


class BundlePage(Orderable):
    parent = ParentalKey("Bundle", related_name="bundled_pages", on_delete=models.CASCADE)
    page = models.ForeignKey(  # type: ignore[var-annotated]
        "wagtailcore.Page", blank=True, null=True, on_delete=models.SET_NULL
    )

    panels: ClassVar[list["Panel"]] = [
        PageChooserWithStatusPanel("page"),
    ]

    def __str__(self) -> str:
        return f"BundlePage: page {self.page_id} in bundle {self.parent_id}"


class BundleDataset(Orderable):
    parent = ParentalKey("Bundle", related_name="bundled_datasets", on_delete=models.CASCADE)
    dataset = models.ForeignKey(  # type: ignore[var-annotated]
        "datasets.Dataset", blank=True, null=True, on_delete=models.SET_NULL
    )

    panels: ClassVar[list["Panel"]] = ["dataset"]

    def __str__(self) -> str:
        return f"BundleDataset: dataset {self.dataset_id} in bundle {self.parent_id}"


class BundleTeam(Orderable):
    parent = ParentalKey("Bundle", on_delete=models.CASCADE, related_name="teams")
    team: "models.ForeignKey[Team]" = models.ForeignKey("teams.Team", on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f"BundleTeam: {self.pk} bundle {self.parent_id} team: {self.team_id}"


class BundlesQuerySet(QuerySet):
    def active(self) -> Self:
        """Provides a pre-filtered queryset for active bundles. Usage: Bundle.objects.active()."""
        return self.filter(status__in=ACTIVE_BUNDLE_STATUSES)

    def editable(self) -> Self:
        """Provides a pre-filtered queryset for editable bundles. Usage: Bundle.objects.editable()."""
        return self.filter(status__in=EDITABLE_BUNDLE_STATUSES)

    def previewable(self) -> Self:
        return self.filter(status__in=PREVIEWABLE_BUNDLE_STATUSES)


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
    status = models.CharField(choices=BundleStatus.choices, default=BundleStatus.DRAFT, max_length=32)

    objects = BundleManager()

    panels: ClassVar[list["Panel"]] = [
        FieldPanel("name"),
        FieldRowPanel(
            [
                FieldPanel(
                    "release_calendar_page",
                    heading="Release Calendar page",
                    widget=FutureReleaseCalendarChooserWidget,
                ),
                FieldPanel("publication_date", datetime_widget, heading="or Publication date"),
            ],
            heading="Scheduling",
            icon="calendar",
        ),
        "status",
        InlinePanel("bundled_pages", heading="Bundled pages", icon="doc-empty", label="Page"),
        MultipleChooserPanel(
            "bundled_datasets", heading="Data API datasets", label="Dataset", chooser_field_name="dataset"
        ),
        MultipleChooserPanel(
            "teams", heading="Preview teams", icon="user", label="Preview team", chooser_field_name="team"
        ),
        # these are handled by the form
        FieldPanel("approved_by", classname="hidden w-hidden"),
        FieldPanel("approved_at", classname="hidden w-hidden"),
    ]

    search_fields: ClassVar[list[index.BaseField]] = [
        index.SearchField("name"),
        index.AutocompleteField("name"),
        index.FilterField("status"),
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

    @cached_property
    def active_team_ids(self) -> list[int]:
        return list(self.teams.filter(team__is_active=True).values_list("team__pk", flat=True))

    @property
    def can_be_approved(self) -> bool:
        """Determines whether the bundle can be approved.

        That is, the bundle is in review and all the bundled pages are ready to publish.
        """
        if self.status != BundleStatus.IN_REVIEW:
            return False

        return all(is_page_ready_to_publish(page) for page in self.get_bundled_pages())

    @property
    def is_ready_to_be_published(self) -> bool:
        return self.status == BundleStatus.APPROVED

    def get_bundled_pages(self, specific: bool = False) -> "PageQuerySet[Page]":
        pages = Page.objects.filter(pk__in=self.bundled_pages.values_list("page__pk", flat=True))
        if specific:
            pages = pages.specific().defer_streamfields()
        return pages

    def get_pages_for_previewers(self) -> list[Page]:
        return [
            page
            for page in self.get_bundled_pages(specific=True).not_type(PREVIEWER_EXCLUDED_PAGE_TYPES)
            if is_page_ready_to_preview(page)
        ]

    def get_teams_display(self) -> str:
        return ", ".join(
            list(self.teams.values_list("team__name", flat=True)) or ["-"],
        )
