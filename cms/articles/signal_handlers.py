from typing import TYPE_CHECKING

from django.dispatch import receiver
from wagtail.models import Page
from wagtail.signals import init_new_page, page_published

from cms.articles.models import StatisticalArticlePage

if TYPE_CHECKING:
    from wagtail.admin.views.pages.create import CreateView


@receiver(page_published, sender=StatisticalArticlePage)
def on_statistical_article_page_published(
    sender: StatisticalArticlePage,  # pylint: disable=unused-argument
    instance: StatisticalArticlePage,
    **kwargs: dict,
) -> None:
    """Signal handler for when a StatisticalArticlePage is published."""
    # Go through the updates streamfield and set frozen to true for all corrections
    for correction in instance.corrections:
        correction.value["frozen"] = True

    instance.save(update_fields=["corrections"])


@receiver(init_new_page)
def prepopulate_statistical_article(
    sender: type[CreateView],  # pylint: disable=unused-argument
    page: Page,
    parent: Page,
    **kwargs: dict,
) -> None:
    if not isinstance(page, StatisticalArticlePage):
        return

    # Get the latest page in the series
    latest = parent.get_latest()

    if not latest:
        return

    # Prepopulate the new page with the latest page's data
    page.summary = latest.summary
    page.headline_figures = latest.headline_figures
    page.contact_details = latest.contact_details
    page.is_accredited = latest.is_accredited
    page.is_census = latest.is_census
    page.search_description = latest.search_description
    page.datasets = latest.datasets
    page.dataset_sorting = latest.dataset_sorting
