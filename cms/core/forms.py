from django.forms import ValidationError
from wagtail.models import PageLogEntry

from cms.taxonomy.forms import DeduplicateTopicsAdminForm


class PageWithCorrectionsAdminForm(DeduplicateTopicsAdminForm):
    def clean_corrections(self) -> list:  # noqa: C901
        corrections: list = self.cleaned_data["corrections"]

        if self.instance.pk is None:
            if corrections:
                self.add_error(
                    "corrections",
                    ValidationError(
                        "You cannot create a notice or correction for a page that has not been created yet"
                    ),
                )
            return corrections

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
        last_date = None
        latest_correction_version = 0

        for correction in corrections:
            # Check if more than one new correction is being added
            if not correction.value["frozen"]:
                if new_correction:
                    self.add_error("updates", ValidationError("Only one new correction can be published at a time"))
                    break
                new_correction = correction

            # Check if the order is chronological (newest first, descending)
            if last_date and correction.value["when"] > last_date:
                self.add_error("updates", ValidationError("Corrections must be in chronological, descending order"))
                break
            last_date = correction.value["when"]

            latest_correction_version = max(latest_correction_version, correction.value["version_id"] or 0)

            if (
                correction.value["previous_version"]
                and int(correction.value["previous_version"]) not in page_revision_ids
            ):
                # Prevent tampering
                self.add_error("updates", ValidationError("The chosen revision is not valid for the current page"))
            elif latest_published_revision_id is not None:
                # If there's no value, set it to the latest revision
                correction.value["previous_version"] = latest_published_revision_id

        if new_correction and not new_correction.value["version_id"]:
            new_correction.value["version_id"] = latest_correction_version + 1

        return corrections
