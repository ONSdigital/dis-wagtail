from typing import Any

from django import forms

from cms.core.forms import DeduplicateInlinePanelAdminForm


class TopicPageAdminForm(DeduplicateInlinePanelAdminForm):
    topic_page_id = forms.CharField(required=False, widget=forms.HiddenInput())

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        if self.instance.pk:
            self.fields["topic_page_id"].initial = self.instance.pk

    def clean(self) -> dict[str, Any] | None:
        cleaned_data: dict[str, Any] = super().clean()

        cleaned_data.pop("topic_page_id", None)

        self.deduplicate_nullable_page_formset("related_articles")
        self.deduplicate_nullable_page_formset("related_methodologies")

        return cleaned_data
