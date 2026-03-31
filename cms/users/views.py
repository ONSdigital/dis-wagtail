from typing import cast

from django import forms
from wagtail import hooks
from wagtail.admin.views.account import (
    AccountView,
    AvatarSettingsPanel,
    BaseSettingsPanel,
    LocaleSettingsPanel,
    NameEmailSettingsPanel,
    NotificationsSettingsPanel,
    ThemeSettingsPanel,
)
from wagtail.users.models import UserProfile


class ReadOnlyNameEmailSettingsPanel(NameEmailSettingsPanel):
    def get_form(self) -> forms.BaseForm:
        form = cast(forms.BaseForm, super().get_form())
        for field in form.fields.values():
            field.disabled = True
            field.required = False
        return form


class ReadOnlyAvatarSettingsPanel(AvatarSettingsPanel):
    template_name = "wagtailadmin/account/settings_panels/avatar_readonly.html"

    def get_form(self) -> forms.BaseForm:
        return cast(forms.BaseForm, self.form_class(instance=self.profile, prefix=self.name))


class ReadOnlyLocaleSettingsPanel(LocaleSettingsPanel):
    def get_form(self) -> forms.BaseForm:
        form = cast(forms.BaseForm, super().get_form())
        for field in form.fields.values():
            field.disabled = True
            field.required = False
        return form


class ONSAccountView(AccountView):
    def get_panels(self) -> list[BaseSettingsPanel]:
        request = self.request
        user = request.user
        profile = UserProfile.get_for_user(user)

        panels = [
            ReadOnlyNameEmailSettingsPanel(request, user, profile),
            ReadOnlyAvatarSettingsPanel(request, user, profile),
            NotificationsSettingsPanel(request, user, profile),
            ReadOnlyLocaleSettingsPanel(request, user, profile),
            ThemeSettingsPanel(request, user, profile),
        ]

        for fn in hooks.get_hooks("register_account_settings_panel"):
            panel = fn(request, user, profile)
            if panel and panel.is_active():
                panels.append(panel)

        return [panel for panel in panels if panel.is_active()]
