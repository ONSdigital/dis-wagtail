from typing import TYPE_CHECKING, Any, ClassVar

from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _
from wagtail.fields import RichTextField
from wagtail.models import RevisionMixin, TranslatableMixin
from wagtail.search import index

if TYPE_CHECKING:
    from wagtail.admin.panels import Panel


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
        *index.Indexed.search_fields,
        index.SearchField("name"),
        index.AutocompleteField("name"),
        index.SearchField("email"),
        index.AutocompleteField("email"),
        index.SearchField("phone"),
    ]

    class Meta:
        verbose_name = _("contact details")
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
        if self.name:
            self.name = self.name.strip()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return str(self.name)


class GlossaryTerm(TranslatableMixin, RevisionMixin, index.Indexed, models.Model):
    """A model for glossary terms."""

    title = models.CharField(max_length=255)
    definition = RichTextField(features=settings.RICH_TEXT_BASIC)
    # to allow for a user to be set on creation and seen in the IndexView
    updated_by = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="glossary_terms",
    )
    # See https://docs.wagtail.org/en/stable/advanced_topics/reference_index.html
    updated_by.wagtail_reference_index_ignore = True  # type: ignore[attr-defined]

    revisions = GenericRelation("wagtailcore.Revision", related_query_name="glossary_term")

    panels: ClassVar[list["Panel"]] = [
        "title",
        "definition",
    ]

    search_fields: ClassVar[list[index.BaseField]] = [
        *index.Indexed.search_fields,
        index.SearchField("title"),
        index.AutocompleteField("title"),
        index.SearchField("definition"),
        index.AutocompleteField("definition"),
    ]

    class Meta:
        verbose_name = _("glossary term")
        verbose_name_plural = _("glossary terms")

        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                Lower("title"),
                name="core_glossary_term_title_unique",
                violation_error_message=_("A glossary term with this title already exists."),
            ),
            models.UniqueConstraint(
                fields=("translation_key", "locale"), name="unique_translation_key_locale_core_glossaryterm"
            ),
        ]

    def __str__(self) -> str:
        return str(self.title)

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.title:
            self.title = self.title.strip()
        super().save(*args, **kwargs)
