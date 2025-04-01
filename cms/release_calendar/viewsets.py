from django.db.models import QuerySet
from django.utils import timezone
from wagtail.admin.ui.tables import Column, DateColumn
from wagtail.admin.views.generic.chooser import ChooseResultsView, ChooseView
from wagtail.admin.viewsets.chooser import ChooserViewSet

from cms.release_calendar.enums import ReleaseStatus
from cms.release_calendar.models import ReleaseCalendarPage


class FutureReleaseCalendarMixin:
    def get_object_list(self) -> QuerySet[ReleaseCalendarPage]:
        return ReleaseCalendarPage.objects.exclude(
            status__in=[ReleaseStatus.CANCELLED, ReleaseStatus.PUBLISHED]
        ).exclude(release_date__lt=timezone.now())

    @property
    def columns(self) -> list[Column]:
        return [
            self.title_column,  # type: ignore[attr-defined]
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


class FutureReleaseCalendarPageChooserViewSet(ChooserViewSet):
    model = ReleaseCalendarPage
    choose_view_class = FutureReleaseCalendarPageChooseView
    choose_results_view_class = FutureReleaseCalendarPageChooseResultsView
    register_widget = False

    icon = "calendar-check"
    choose_one_text = "Choose Release Calendar page"
    choose_another_text = "Choose another Release Calendar page"
    edit_item_text = "Edit Release Calendar page"


release_calendar_chooser_viewset = FutureReleaseCalendarPageChooserViewSet("release_calendar_chooser")
FutureReleaseCalendarChooserWidget = release_calendar_chooser_viewset.widget_class
