from typing import TYPE_CHECKING, Any

from django.db.models import CharField

if TYPE_CHECKING:
    from django.forms import Field


class NonStrippingCharField(CharField):
    def formfield(self, *args: Any, **kwargs: Any) -> Field:
        kwargs["strip"] = False
        return super().formfield(*args, **kwargs)  # type: ignore[return-value]
