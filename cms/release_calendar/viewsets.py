from typing import TYPE_CHECKING

from django.db.models import Q, QuerySet
from django.utils import timezone
from wagtail.admin.ui.tables import Column, DateColumn, LocaleColumn
from wagtail.admin.views.generic.chooser import ChooseResultsView, ChooseView, ChosenView
from wagtail.admin.viewsets.chooser import ChooserViewSet
from wagtail.permission_policies.pages import PagePermissionPolicy

from cms.bundles.enums import ACTIVE_BUNDLE_STATUSES

from .enums import ReleaseStatus
from .utils import get_release_calendar_page_details

if TYPE_CHECKING:
    from wagtail.admin.widgets import BaseChooser

    from cms.release_calendar.models import ReleaseCalendarPage


class FutureReleaseCalendarMixin:
    results_template_name = "wagtailadmin/panels/future_release_calendar_page_chooser_results.html"

    def get_object_list(self) -> QuerySet["ReleaseCalendarPage"]:
        # To avoid circular import
        from cms.release_calendar.models import ReleaseCalendarPage  # pylint: disable=import-outside-toplevel

        # note: using this method to allow search to work without adding the bundle data in the index
        explorable_pages = PagePermissionPolicy().explorable_instances(self.request.user)  # type: ignore[attr-defined]

        calendar_pages_to_exclude_qs = ReleaseCalendarPage.objects.filter(
            Q(status__in=[ReleaseStatus.CANCELLED, ReleaseStatus.PUBLISHED])
            | Q(release_date__lt=timezone.now())
            | Q(bundles__status__in=ACTIVE_BUNDLE_STATUSES)
            | Q(alias_of__isnull=False)
        )
        pages: QuerySet[ReleaseCalendarPage] = (
            explorable_pages.type(ReleaseCalendarPage)
            .specific()
            .defer_streamfields()
            .exclude(pk__in=calendar_pages_to_exclude_qs)
        )
        return pages

    @property
    def columns(self) -> list[Column]:
        return [
            self.title_column,  # type: ignore[attr-defined]
            LocaleColumn(classname="w-text-16 w-w-[120px]"),  # w-w-[120px] is used to adjust the width
            Column("release_date"),
            Column("release_status", label="Status", accessor="get_status_display"),
            DateColumn(
                "updated",
                label="Last Updated",
                width="12%",
                accessor="latest_revision_created_at",
            ),
        ]


class FutureReleaseCalendarPageChooseView(FutureReleaseCalendarMixin, ChooseView): ...


class FutureReleaseCalendarPageChooseResultsView(FutureReleaseCalendarMixin, ChooseResultsView): ...


class FutureReleaseCalendarPageChosenMixin(ChosenView):
    def get_display_title(self, instance: "ReleaseCalendarPage") -> str:
        return get_release_calendar_page_details(instance)


class FutureReleaseCalendarPageChooserViewSet(ChooserViewSet):
    # Used a string reference so the model is lazily loaded and circular imports are avoided
    model = "release_calendar.ReleaseCalendarPage"
    choose_view_class = FutureReleaseCalendarPageChooseView
    choose_results_view_class = FutureReleaseCalendarPageChooseResultsView
    chosen_view_class = FutureReleaseCalendarPageChosenMixin
    register_widget = False

    icon = "calendar-check"
    choose_one_text = "Choose Release Calendar page"
    choose_another_text = "Choose another Release Calendar page"
    edit_item_text = "Edit Release Calendar page"


release_calendar_chooser_viewset = FutureReleaseCalendarPageChooserViewSet("release_calendar_chooser")
FutureReleaseCalendarChooserWidget: type["BaseChooser"] = release_calendar_chooser_viewset.widget_class
