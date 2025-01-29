from wagtail.admin.viewsets.chooser import ChooserViewSet

from cms.taxonomy.models import Topic


class TopicChooserViewSet(ChooserViewSet):
    model = Topic

    icon = "tag"
    choose_one_text = "Choose a topic"
    choose_another_text = "Choose another topic"


topic_chooser_viewset = TopicChooserViewSet("topic_chooser")
