from django.db.models import Q, QuerySet
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from wagtail.admin.ui.tables import Column, DateColumn
from wagtail.admin.views.generic.chooser import ChooseResultsView, ChooseView
from wagtail.admin.viewsets.chooser import ChooserViewSet

from cms.bundles.enums import ACTIVE_BUNDLE_STATUSES
from cms.release_calendar.enums import ReleaseStatus
from cms.release_calendar.models import ReleaseCalendarPage


class FutureReleaseCalendarMixin:
    results_template_name = "release_calendar/future_release_calendar_page_chooser_results.html"

    def get_object_list(self) -> QuerySet[ReleaseCalendarPage]:
        # note: using this method to allow search to work without adding the bundle data in the index
        calendar_pages_to_exclude_qs = ReleaseCalendarPage.objects.filter(
            Q(status__in=[ReleaseStatus.CANCELLED, ReleaseStatus.PUBLISHED])
            | Q(release_date__lt=timezone.now())
            | Q(bundles__status__in=ACTIVE_BUNDLE_STATUSES)
        )
        return ReleaseCalendarPage.objects.exclude(pk__in=calendar_pages_to_exclude_qs)

    @property
    def columns(self) -> list[Column]:
        return [
            self.title_column,  # type: ignore[attr-defined]
            Column("release_date"),
            Column("release_status", label=_("Status"), accessor="get_status_display"),
            DateColumn(
                "updated",
                label=_("Last Updated"),
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
    choose_one_text = _("Choose Release Calendar page")
    choose_another_text = _("Choose another Release Calendar page")
    edit_item_text = _("Edit Release Calendar page")


release_calendar_chooser_viewset = FutureReleaseCalendarPageChooserViewSet("release_calendar_chooser")
FutureReleaseCalendarChooserWidget = release_calendar_chooser_viewset.widget_class
