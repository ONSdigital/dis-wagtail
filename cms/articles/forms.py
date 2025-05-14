from secrets import token_urlsafe
from typing import Any

from django.forms import ValidationError
from wagtail.blocks.stream_block import StreamValue
from wagtail.models import Page

from cms.articles.utils import FORMULA_INDICATOR, latex_formula_to_svg
from cms.core.forms import PageWithCorrectionsAdminForm
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
                # The figures were inherited via the init_new_page signal, so we need to also inherit the figure ids
                self.instance.headline_figures_figure_ids = latest.headline_figures_figure_ids

        for figure in headline_figures:
            if not figure.value["figure_id"]:
                figure.value["figure_id"] = token_urlsafe(6)
                # Add the generated ID to our list of IDs for validation
                self.instance.add_headline_figures_figure_id(figure.value["figure_id"])

        return headline_figures


class PageWithEquationsAdminForm(DeduplicateTopicsAdminForm):
    def clean_content(self) -> StreamValue:
        content: StreamValue = self.cleaned_data["content"]
        if not content:
            return content

        for section in content:
            for block in section.value["content"]:
                if block.block_type == "equation":
                    equation = block.value["equation"]
                    # Remove $$ from the start and end of the equation
                    if equation.startswith(FORMULA_INDICATOR) and equation.endswith(FORMULA_INDICATOR):
                        equation = equation[2:-2]
                    try:
                        block.value["svg"] = latex_formula_to_svg(equation)
                    except RuntimeError:
                        self.add_error(
                            "content",
                            ValidationError("The equation is not valid LaTeX. Please check the syntax and try again."),
                        )

        return content


class StatisticalArticlePageAdminForm(
    PageWithHeadlineFiguresAdminForm, PageWithCorrectionsAdminForm, PageWithEquationsAdminForm
): ...
