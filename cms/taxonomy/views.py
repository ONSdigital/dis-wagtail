from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _
from wagtail.admin.viewsets.chooser import ChooserViewSet

from cms.taxonomy.models import Topic


class TopicChooserViewSet(ChooserViewSet):
    model = Topic
    icon = "tag"

    choose_one_text = _("Choose a topic")
    choose_another_text = _("Choose a different topic")

    # TODO delete this, it should only be on the Exclusive version
    # def get_object_list(self) -> QuerySet[Topic]:
    #     return Topic.objects.filter(related_themepage=None).filter(related_topicpage=None)


class TopicExclusiveChooserViewSet(TopicChooserViewSet):
    # TODO how to make only the topic/theme page choosers use this viewset?

    def get_object_list(self) -> QuerySet[Topic]:
        """Filter out topics which are already linked to a theme or topic page."""
        # TODO This will need to be updated to support multilingual pages

        # TODO can this query be re-written without explicit knowledge of the different related names?
        return Topic.objects.filter(related_themepage=None).filter(related_topicpage=None)


topic_chooser_viewset = TopicChooserViewSet("topic_chooser")
