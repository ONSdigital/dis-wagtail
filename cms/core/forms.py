from collections.abc import Mapping
from secrets import token_urlsafe
from typing import Any

from django.core.files.uploadedfile import UploadedFile
from django.forms import ValidationError
from django.utils.datastructures import MultiValueDict
from wagtail.blocks.stream_block import StreamValue
from wagtail.models import Page, PageLogEntry

from cms.taxonomy.forms import DeduplicateTopicsAdminForm


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


class PageWithHeadlineFiguresAdminForm(DeduplicateTopicsAdminForm):
    def __init__(
        self,
        *args: Any,
        data: Mapping[str, Any] | None = None,
        files: MultiValueDict[str, UploadedFile] | None = None,
        parent_page: Page | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(data, files, *args, **kwargs)
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
