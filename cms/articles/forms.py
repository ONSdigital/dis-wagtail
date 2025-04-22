from secrets import token_urlsafe
from typing import Any

from wagtail.blocks.stream_block import StreamValue
from wagtail.models import Page

from cms.taxonomy.forms import DeduplicateTopicsAdminForm


class PageWithHeadlineFiguresAdminForm(DeduplicateTopicsAdminForm):
    def __init__(
        self,
        *args: Any,
        parent_page: Page | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        # Save a reference to the parent page which we use in the clean method
        self.parent_page = parent_page

    def clean_headline_figures(self) -> StreamValue:
        headline_figures: StreamValue = self.cleaned_data["headline_figures"]
        if not headline_figures:
            # No headline figures, so return an empty stream value
            return headline_figures

        # Check if editing a new page
        if self.instance.pk is None and self.parent_page:
            # Grab the latest page in the series
            latest = self.parent_page.get_latest()
            if latest:
                # The figures were inherited, so we need to also inherit the figure ids
                self.instance.headline_figures_figure_ids = latest.headline_figures_figure_ids

        for figure in headline_figures[0].value:
            if not figure["figure_id"]:
                figure["figure_id"] = token_urlsafe(6)
                # Add the generated ID to our list of IDs for validation
                self.instance.add_headline_figures_figure_id(figure["figure_id"])

        return headline_figures
