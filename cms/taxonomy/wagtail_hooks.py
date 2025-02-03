from wagtail import hooks

from cms.taxonomy.viewsets import exclusive_topic_chooser_viewset, topic_chooser_viewset


@hooks.register("register_admin_viewset")
def register_topic_chooser_viewset():
    return topic_chooser_viewset


@hooks.register("register_admin_viewset")
def register_exclusive_topic_chooser_viewset():
    return exclusive_topic_chooser_viewset
