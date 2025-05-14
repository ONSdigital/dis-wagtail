# TODO: remove when upgrading to Wagtail 7.0
from functools import wraps
from typing import Any

import wagtail.admin.forms.choosers

original_init = wagtail.admin.forms.choosers.LocaleFilterMixin.__init__


@wraps(original_init)
def new_init(self, *args: Any, **kwargs: Any) -> None:  # type: ignore[no-untyped-def]
    original_init(self, *args, **kwargs)
    self.fields["locale"].choices = [("", "All"), *self.fields["locale"].choices]


wagtail.admin.forms.choosers.LocaleFilterMixin.__init__ = new_init
