from wagtail.admin.forms import WagtailAdminPageForm


class DeDuplicateTopicsAdminForm(WagtailAdminPageForm):
    def clean(self):
        """Wagtail choosers currently do not have the ability to remove already selected values, so the same topic can
        be selected multiple times. This form class overrides the clean method to delete any duplicate topics from the
        form before it is parsed.
        """
        cleaned_data = super().clean()

        if not self.formsets.get("topics"):
            return cleaned_data

        chosen = []

        for idx, form in enumerate(self.formsets["topics"].forms):
            if not form.is_valid():
                continue
            topic = form.clean().get("topic")
            if topic in chosen:
                # Delete duplicate topics
                self.formsets["topics"].forms[idx].cleaned_data["DELETE"] = True
            else:
                chosen.append(topic)

        return cleaned_data
