from typing import Any

from django.db.models.signals import post_save
from django.dispatch import receiver
from wagtail import hooks

from cms.methodology.models import MethodologyIndexPage
from cms.topics.models import TopicPage


@receiver(post_save, sender=TopicPage)
def create_methodology_index_page(sender: Any, instance: TopicPage, created: bool, raw: bool, **kwargs: Any) -> None:  # pylint: disable=unused-argument
    if not created or raw:
        return

    if instance.alias_of_id is not None:
        # If this page is an alias, assume the methodology index is about to be created as an alias, too.
        return

    index_page = MethodologyIndexPage(title="Methodologies")
    instance.add_child(instance=index_page)
    # We publish a live version for the methodologies index page. This is acceptable since its URL redirects
    index_page.save_revision().publish()

    # Run after_create_page hook to ensure translations are created
    # @see https://github.com/wagtail/wagtail/issues/13698
    for fn in hooks.get_hooks("after_create_page"):
        fn(None, index_page)
