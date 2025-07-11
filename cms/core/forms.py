import logging
from typing import Any

from django.forms import ValidationError
from wagtail.admin.forms import WagtailAdminPageForm
from wagtail.admin.forms.choosers import BaseFilterForm, SearchFilterMixin
from wagtail.admin.forms.pages import CopyForm
from wagtail.blocks.stream_block import StreamValue
from wagtail.models import PageLogEntry

from cms.core.utils import FORMULA_INDICATOR, latex_formula_to_svg
from cms.taxonomy.forms import DeduplicateTopicsAdminForm

logger = logging.getLogger(__name__)


LATEX_VALIDATION_ERROR = "The equation is not valid LaTeX. Please check the syntax and try again."


class PageWithCorrectionsAdminForm(DeduplicateTopicsAdminForm):
    def clean_corrections(self) -> StreamValue:  # noqa: C901
        corrections: StreamValue = self.cleaned_data["corrections"]

        if self.instance.pk is None:
            if corrections:
                self.add_error(
                    "corrections",
                    ValidationError(
                        "You cannot create a notice or correction for a page that has not been created yet"
                    ),
                )
            return corrections

        old_frozen_versions = [
            correction.value["version_id"] for correction in self.instance.corrections if correction.value["frozen"]
        ]
        new_frozen_versions = [
            correction.value["version_id"] for correction in corrections if correction.value["frozen"]
        ]

        latest_frozen_date = max(
            (correction.value["when"] for correction in corrections if correction.value["frozen"]), default=None
        )

        # This will check if any frozen corrections are being removed or tampered with
        if old_frozen_versions != new_frozen_versions:
            self.add_error(
                "corrections",
                ValidationError(
                    "You cannot remove a correction that has already been published. "
                    "Please refresh the page and try again."
                ),
            )

        latest_published_revision_id = (
            PageLogEntry.objects.filter(page=self.instance, action="wagtail.publish")
            .order_by("-timestamp")
            .values_list("revision_id", flat=True)
            .first()
        )

        if corrections and not latest_published_revision_id:
            self.add_error(
                "corrections",
                ValidationError("You cannot create a notice or correction for a page that has not been published yet"),
            )

        page_revision_ids = set(self.instance.revisions.order_by().values_list("id", flat=True).distinct())

        new_correction = None
        latest_correction_version = 0

        for correction in corrections:
            # Check if more than one new correction is being added
            if not correction.value["frozen"]:
                if new_correction:
                    self.add_error("corrections", ValidationError("Only one new correction can be published at a time"))
                    break
                new_correction = correction

                if latest_frozen_date and new_correction.value["when"] < latest_frozen_date:
                    self.add_error(
                        "corrections",
                        ValidationError(
                            "You cannot create a correction with a date earlier than the latest correction"
                        ),
                    )

            latest_correction_version = max(latest_correction_version, correction.value["version_id"] or 0)

            if (
                correction.value["previous_version"]
                and int(correction.value["previous_version"]) not in page_revision_ids
            ):
                # Prevent tampering
                self.add_error("corrections", ValidationError("The chosen revision is not valid for the current page"))

        if new_correction:
            if not new_correction.value["version_id"]:
                new_correction.value["version_id"] = latest_correction_version + 1
            if not new_correction.value["previous_version"]:
                new_correction.value["previous_version"] = latest_published_revision_id

        # Sort corrections
        sorted_corrections = sorted(corrections, key=lambda correction: correction.value["when"], reverse=True)

        return StreamValue(corrections.stream_block, sorted_corrections)


class NoLocaleFilterInChoosersForm(SearchFilterMixin, BaseFilterForm):
    """A chooser filter form that deliberately excludes the locale filter."""


class PageWithEquationsAdminForm(WagtailAdminPageForm):
    def _process_content_block(self, block: StreamValue) -> None:
        if block.block_type == "equation":
            equation = block.value["equation"].replace("\n", "").strip()
            if equation.startswith(FORMULA_INDICATOR):
                if not equation.endswith(FORMULA_INDICATOR):
                    # Not worth trying to parse the equation if it doesn't end with the indicator
                    self.add_error("content", ValidationError(LATEX_VALIDATION_ERROR))
                    return
                equation = equation[2:-2]
            try:
                block.value["svg"] = latex_formula_to_svg(equation)
            except RuntimeError as error:
                # Log the error for debugging purposes
                logger.warning(
                    "Could not process LaTeX equation: %s",
                    error,
                    extra={
                        "equation": equation,
                    },
                )
                self.add_error("content", LATEX_VALIDATION_ERROR)

    def clean_content(self) -> StreamValue:
        content: StreamValue = self.cleaned_data["content"]
        if not content:
            return content

        for block in content:
            if block.block_type == "section":
                for sub_block in block.value["content"]:
                    self._process_content_block(sub_block)
            else:
                self._process_content_block(block)

        return content


class ONSCopyForm(CopyForm):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        if "publish_copies" in self.fields:
            del self.fields["publish_copies"]
        if "alias" in self.fields:
            del self.fields["alias"]
