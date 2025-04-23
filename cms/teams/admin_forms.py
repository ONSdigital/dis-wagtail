from typing import Any

from django import forms
from django.conf import settings
from wagtail.admin.forms import WagtailAdminModelForm

from cms.teams.models import Team
from cms.users.models import User


class TeamAdminForm(WagtailAdminModelForm):
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(), widget=forms.CheckboxSelectMultiple(), required=False
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        if self.instance.pk:
            self.fields["users"].initial = self.instance.users.all()

    def save(self, commit: bool = True) -> Team:
        instance: Team = super().save(commit=False)
        if commit:
            instance.save()
            instance.users.set(self.cleaned_data["users"])
        return instance

    class Meta(WagtailAdminModelForm.Meta):
        model = Team
        fields = ["name", "identifier", "users"] if settings.ALLOW_TEAM_MANAGEMENT else ["name"]
