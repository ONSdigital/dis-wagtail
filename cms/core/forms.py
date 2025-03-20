from django.forms import ValidationError
from wagtail.models import PageLogEntry

from cms.taxonomy.forms import DeduplicateTopicsAdminForm


class PageWithUpdatesAdminForm(DeduplicateTopicsAdminForm):
    def clean_updates(self):  # noqa: C901
        updates = self.cleaned_data["updates"]

        if self.instance.pk is None:
            if updates:
                self.add_error(
                    "updates",
                    ValidationError(
                        "You cannot create a notice or correction for a page that has not been created yet"
                    ),
                )
            return updates

        latest_published_revision_id = (
            PageLogEntry.objects.filter(page=self.instance, action="wagtail.publish")
            .order_by("-timestamp")
            .values_list("revision_id", flat=True)
            .first()
        )

        if updates and not latest_published_revision_id:
            self.add_error(
                "updates",
                ValidationError("You cannot create a notice or correction for a page that has not been published yet"),
            )

        page_revision_ids = set(self.instance.revisions.order_by().values_list("id", flat=True).distinct())

        new_correction = None
        last_date = None
        latest_correction_version = 0

        for update in updates:
            if update.block_type != "correction":
                continue

            # Check if more than one new correction is being added
            if not update.value["frozen"]:
                if new_correction:
                    self.add_error("updates", ValidationError("Only one new correction can be published at a time"))
                    break
                new_correction = update

            # Check if the order is chronological (newest first, descending)
            if last_date and update.value["when"] > last_date:
                self.add_error("updates", ValidationError("Corrections must be in chronological, descending order"))
                break
            last_date = update.value["when"]

            latest_correction_version = max(latest_correction_version, update.value["version_id"] or 0)

            if update.value["previous_version"] and int(update.value["previous_version"]) not in page_revision_ids:
                # Prevent tampering
                self.add_error("updates", ValidationError("The chosen revision is not valid for the current page"))
            elif latest_published_revision_id is not None:
                # If there's no value, set it to the latest revision
                update.value["previous_version"] = latest_published_revision_id

        if new_correction and not new_correction.value["version_id"]:
            new_correction.value["version_id"] = latest_correction_version + 1

        return updates
