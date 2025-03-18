from django.forms import ValidationError
from wagtail.models import PageLogEntry

from cms.taxonomy.forms import DeduplicateTopicsAdminForm


class PageWithUpdatesAdminForm(DeduplicateTopicsAdminForm):
    def clean_updates(self):
        updates = self.cleaned_data["updates"]

        latest_published_revision_id = (
            PageLogEntry.objects.filter(page=self.instance, action="wagtail.publish")
            .order_by("-timestamp")
            .values_list("revision_id", flat=True)
            .first()
        )
        page_revision_ids = set(self.instance.revisions.order_by().values_list("id", flat=True).distinct())

        for update in updates:
            if update.block_type != "correction":
                continue

            if update.value["previous_version"] and int(update.value["previous_version"]) not in page_revision_ids:
                # Prevent tampering
                self.add_error("updates", ValidationError("The chosen revision is not valid for the current page"))
            elif latest_published_revision_id is not None:
                # If there's no value, set it to the latest revision
                update.value["previous_version"] = latest_published_revision_id

        return updates
