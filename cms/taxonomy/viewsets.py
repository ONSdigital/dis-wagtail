from django.conf import settings
from django.db.models import QuerySet
from wagtail.admin.ui.tables import Column
from wagtail.admin.views.generic.chooser import ChooseResultsView, ChooseView
from wagtail.admin.viewsets.chooser import ChooserViewSet

from cms.taxonomy.models import Topic


class TopicChooseViewMixin:
    model_class = Topic

    def get_object_list(self) -> QuerySet[Topic]:
        return self.model_class.objects.all().order_by("path")  # type: ignore[no-any-return]

    @property
    def columns(self) -> list[Column]:
        return [
            *getattr(super(), "columns", []),
            Column("parent_topics", label="Parent Topics", accessor="display_parent_topics"),
        ]


class TopicChooseView(TopicChooseViewMixin, ChooseView): ...


class TopicChooseResultsView(TopicChooseViewMixin, ChooseResultsView): ...


class TopicChooserViewSet(ChooserViewSet):
    model = Topic
    icon = "tag"

    choose_one_text = "Choose a topic"
    choose_another_text = "Choose a different topic"

    choose_view_class = TopicChooseView
    choose_results_view_class = TopicChooseResultsView


class ExclusiveTopicChooserViewSet(TopicChooserViewSet):
    register_widget = False

    def get_object_list(self) -> QuerySet[Topic]:
        """Filter out topics which are already linked to a theme or topic page."""
        # TODO This will need to be updated to support multilingual pages... how?
        # Get the HTTP_REFERER from meta request headers, extract the page type either from the URL or by looking up
        # the page ID to get the page type.

        if not settings.ENFORCE_EXCLUSIVE_TAXONOMY:
            return Topic.objects.all()  # type: ignore[no-any-return]
        return Topic.objects.filter(related_themepage=None, related_topicpage=None)  # type: ignore[no-any-return]


topic_chooser_viewset = TopicChooserViewSet("topic_chooser")

exclusive_topic_chooser_viewset = ExclusiveTopicChooserViewSet("exclusive_topic_chooser")

ExclusiveTopicChooserWidget = exclusive_topic_chooser_viewset.widget_class
