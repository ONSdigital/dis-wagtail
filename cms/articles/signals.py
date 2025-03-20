from django.dispatch import receiver
from wagtail.signals import page_published

from cms.articles.models import StatisticalArticlePage


@receiver(page_published, sender=StatisticalArticlePage)
def on_statistical_article_page_published(_, instance, **kwargs):
    """Signal handler for when a StatisticalArticlePage is published."""
    # Go through the updates streamfield and set frozen to true for all corrections
    for update in instance.updates:
        if update.block_type == "correction":
            update.value["frozen"] = True

    instance.save(update_fields=["updates"])
