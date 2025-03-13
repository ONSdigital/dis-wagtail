from collections.abc import Collection
from typing import TYPE_CHECKING, Any, ClassVar, Optional

from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _
from wagtail.fields import RichTextField
from wagtail.models import PreviewableMixin, RevisionMixin, TranslatableMixin
from wagtail.search import index

if TYPE_CHECKING:
    from django.http import HttpRequest
    from wagtail.admin.panels import Panel

    from cms.users.models import User


class ContactDetails(index.Indexed, models.Model):
    """A model for contact details.

    Note that this is registered as a snippet in core.wagtail_hooks to allow customising the icon.
    """

    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=255, blank=True)

    panels: ClassVar[list["Panel"]] = [
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
    ]

    class Meta:
        verbose_name_plural = _("contact details")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                Lower("name"),
                Lower("email"),
                name="core_contactdetails_name_unique",
                violation_error_message=_("Contact details with this name and email combination already exists."),
            ),
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.name = self.name.strip()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return str(self.name)


class GlossaryTerm(TranslatableMixin, PreviewableMixin, RevisionMixin, index.Indexed, models.Model):
    """A model for glossary terms."""

    name = models.CharField(max_length=255)
    definition = RichTextField(features=settings.RICH_TEXT_BASIC)
    owner = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="owned_glossary_terms",
    )

    revisions = GenericRelation("wagtailcore.Revision", related_query_name="glossary_term")

    panels: ClassVar[list["Panel"]] = [
        "name",
        "definition",
        "owner",
    ]

    search_fields: ClassVar[list[index.BaseField]] = [
        index.SearchField("name"),
        index.AutocompleteField("name"),
        index.SearchField("definition"),
        index.AutocompleteField("definition"),
    ]

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                Lower("name"),
                name="core_glossary_term_name_unique",
                violation_error_message=_("A glossary term with this name already exists."),
            ),
            models.UniqueConstraint(
                fields=("translation_key", "locale"), name="unique_translation_key_locale_core_glossaryterm"
            ),
        ]

    @property
    def updated_by(self) -> Optional["User"]:
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

    def get_preview_template(self, request: "HttpRequest", mode_name: str) -> str:
        return "templates/components/glossary/glossary_term_preview.html"

    def __str__(self) -> str:
        return str(self.name)
