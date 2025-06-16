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

        return cleaned_data
