from typing import Any

from wagtail.admin.forms import WagtailAdminPageForm


class DeduplicateTopicsAdminForm(WagtailAdminPageForm):
    def clean(self) -> dict[str, Any] | None:
        """Wagtail choosers currently do not have the ability to remove already selected values, so the same topic can
        be selected multiple times. This form class overrides the clean method to delete any duplicate topics from the
        form before it is parsed.
        """
        cleaned_data: dict[str, Any] | None = super().clean()

        if not self.formsets.get("topics"):
            return cleaned_data

        chosen = set()

        for idx, form in enumerate(self.formsets["topics"].forms):
            if not form.is_valid():
                continue
            topic = form.clean().get("topic")
            if topic in chosen:
                # Delete duplicate topics
                self.formsets["topics"].forms[idx].cleaned_data["DELETE"] = True
            else:
                chosen.add(topic)

        return cleaned_data
