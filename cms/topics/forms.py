from typing import Any

from django import forms
from wagtail.admin.forms import WagtailAdminPageForm


class TopicPageAdminForm(WagtailAdminPageForm):
    topic_page_id = forms.CharField(required=False, widget=forms.HiddenInput())

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        if self.instance.pk:
            self.fields["topic_page_id"].initial = self.instance.pk

    def _deduplicate_nullable_page_formset(self, formset_name: str) -> None:
        # `page` is nullable on these formsets (external URL rows have page=None), so we
        # skip None rows rather than deleting them — unlike deduplicate_formset() which
        # would mark them for deletion.
        formset = self.formsets.get(formset_name)
        if not formset:
            return
        seen_pages: set = set()
        for index, form in enumerate(formset.forms):
            if not form.is_valid():
                continue
            internal_page = form.clean().get("page")
            if internal_page is None:
                continue
            if internal_page in seen_pages:
                formset.forms[index].cleaned_data["DELETE"] = True
            else:
                seen_pages.add(internal_page)

    def clean(self) -> dict[str, Any] | None:
        cleaned_data: dict[str, Any] = super().clean()

        cleaned_data.pop("topic_page_id", None)

        self._deduplicate_nullable_page_formset("related_articles")
        self._deduplicate_nullable_page_formset("related_methodologies")

        return cleaned_data
