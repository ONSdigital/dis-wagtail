from collections.abc import Collection
from typing import TYPE_CHECKING, Any, ClassVar

from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower
from wagtail.fields import RichTextField
from wagtail.models import PreviewableMixin, RevisionMixin, TranslatableMixin
from wagtail.search import index

if TYPE_CHECKING:
    from django.http import HttpRequest
    from wagtail.admin.panels import Panel

    from cms.users.models import User


class ContactDetails(TranslatableMixin, index.Indexed, models.Model):
    """A model for contact details.

    Note that this is registered as a snippet in core.wagtail_hooks to allow customising the icon.
    """

    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=255, blank=True)

    panels: ClassVar[list[Panel]] = [
        "name",
        "email",
        "phone",
    ]

    search_fields: ClassVar[list[index.BaseField]] = [
        index.SearchField("name"),
        index.AutocompleteField("name"),
        index.SearchField("email"),
        index.AutocompleteField("email"),
        index.SearchField("phone"),
        index.FilterField("locale"),
    ]

    class Meta(TranslatableMixin.Meta):
        verbose_name_plural = "contact details"
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                Lower("name"),
                Lower("email"),
                "locale",
                name="core_contactdetails_name_unique",
                violation_error_message="Contact details with this name and email combination already exists.",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        queryset = ContactDetails.objects.filter(
            name__iexact=self.name.strip(), email__iexact=self.email.strip(), locale=self.locale_id
        )
        if self.pk:
            queryset = queryset.exclude(pk=self.pk)
        if queryset.exists():
            raise ValidationError("Contact details with this name and email combination already exists.")

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.name = self.name.strip()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return str(self.name)


class Definition(TranslatableMixin, PreviewableMixin, RevisionMixin, index.Indexed, models.Model):
    """A model for definitions."""

    # Note: Definitions were formerly known as GlossaryTerms

    name = models.CharField(max_length=255)
    definition = RichTextField(features=settings.RICH_TEXT_BASIC)
    owner = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="owned_definitions",
    )

    revisions = GenericRelation("wagtailcore.Revision", related_query_name="definition")

    panels: ClassVar[list[Panel]] = [
        "name",
        "definition",
        "owner",
    ]

    search_fields: ClassVar[list[index.BaseField]] = [
        index.SearchField("name"),
        index.AutocompleteField("name"),
        index.SearchField("definition"),
        index.AutocompleteField("definition"),
        index.FilterField("locale"),
    ]

    class Meta:
        verbose_name = "definition"
        verbose_name_plural = "definitions"
        unique_together: ClassVar[list[tuple[str, ...]]] = [*TranslatableMixin.Meta.unique_together, ("name", "locale")]

    @property
    def updated_by(self) -> User | None:
        return self.latest_revision.user if self.latest_revision else None

    def validate_unique(self, exclude: Collection[str] | None = None) -> None:
        # Include the locale field for validation as it's not included by default
        # See https://github.com/wagtail/wagtail/issues/8918#issuecomment-1208670360
        if exclude and "locale" in exclude:
            exclude.remove("locale")  # type: ignore[attr-defined]
        return super().validate_unique(exclude)

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.name = self.name.strip()
        super().save(*args, **kwargs)

    def get_preview_template(self, request: HttpRequest, mode_name: str) -> str:
        return "templates/components/definitions/definition_preview.html"

    def __str__(self) -> str:
        return str(self.name)
