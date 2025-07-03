from typing import TYPE_CHECKING

from wagtail import hooks

from cms.methodology.models import MethodologyIndexPage

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse

    from cms.topics.models import TopicPage


@hooks.register("after_create_topic_page")
def after_create_topic_page(request: "HttpRequest", topic_page: "TopicPage") -> "HttpResponse | None":
    index_page = MethodologyIndexPage(title="Methodologies")
    topic_page.add_child(instance=index_page)
    index_page.save_revision().publish()

    for fn in hooks.get_hooks("after_create_page"):
        fn(request, index_page)
