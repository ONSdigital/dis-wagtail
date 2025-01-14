from django.db.models import CharField


class NonStrippingCharField(CharField):
    def formfield(self, **kwargs):
        kwargs["strip"] = False
        return super().formfield(**kwargs)
