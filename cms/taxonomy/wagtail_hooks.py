from wagtail import hooks

from cms.taxonomy.viewsets import (
    ExclusiveTopicChooserViewSet,
    TopicChooserViewSet,
    exclusive_topic_chooser_viewset,
    topic_chooser_viewset,
)


@hooks.register("register_admin_viewset")
def register_topic_chooser_viewset() -> TopicChooserViewSet:
    return topic_chooser_viewset


@hooks.register("register_admin_viewset")
def register_exclusive_topic_chooser_viewset() -> ExclusiveTopicChooserViewSet:
    return exclusive_topic_chooser_viewset
