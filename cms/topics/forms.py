from typing import Any

from django import forms
from wagtail.admin.forms import WagtailAdminPageForm


class TopicPageAdminForm(WagtailAdminPageForm):
    topic_page_id = forms.CharField(required=False, widget=forms.HiddenInput())

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        if self.instance.pk:
            self.fields["topic_page_id"].initial = self.instance.pk

    def clean(self) -> dict[str, Any] | None:
        cleaned_data: dict[str, Any] = super().clean()

        # remove topic_page_id before save
        cleaned_data.pop("topic_page_id", None)

        # DeduplicateInlinePanelAdminForm.deduplicate_formset() can't be used here because it
        # marks None-field entries as deleted. The `page` field is nullable (external URL rows
        # have page=None), so using it would incorrectly remove those rows.
        related_articles_formset = self.formsets.get("related_articles")
        if related_articles_formset:
            seen_pages: set = set()
            for index, article_form in enumerate(related_articles_formset.forms):
                if not article_form.is_valid():
                    continue
                internal_page = article_form.clean().get("page")
                if internal_page is None:
                    continue
                if internal_page in seen_pages:
                    related_articles_formset.forms[index].cleaned_data["DELETE"] = True
                else:
                    seen_pages.add(internal_page)

        return cleaned_data
