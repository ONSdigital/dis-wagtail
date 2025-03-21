from typing import ClassVar

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel, MultipleChooserPanel, Panel

from cms.taxonomy.models import Topic
from cms.taxonomy.viewsets import ExclusiveTopicChooserWidget


class ExclusiveTaxonomyMixin(models.Model):
    """A mixin that allows pages to be linked exclusively to a topic."""

    # Note that this is intended to behave as a one-to-one relationship, but multilingual versions of the same page
    # will need to be linked to the same topic, so we need to use a ForeignKey and enforce exclusivity separately
    topic = models.ForeignKey(Topic, on_delete=models.SET_NULL, related_name="related_%(class)s", null=True)

    taxonomy_panels: ClassVar[list["Panel"]] = [
        FieldPanel("topic", widget=ExclusiveTopicChooserWidget),
    ]

    class Meta:
        abstract = True

    def clean(self) -> None:
        super().clean()

        if not self.topic_id:
            raise ValidationError({"topic": _("A topic is required.")})

        if not settings.ENFORCE_EXCLUSIVE_TAXONOMY:
            return

        for exclusive_sub_page_type in ExclusiveTaxonomyMixin.__subclasses__():
            # Check if other pages are exclusively linked to this topic.
            # Translations of the same page are allowed, but other pages aren't.
            # TODO for multilingual support, this will need to exclude different language versions of the same page by
            # excluding matching translation_keys
            qs = exclusive_sub_page_type.objects.filter(topic=self.topic_id)  # type: ignore[attr-defined]
            if not self._state.adding:
                # On edit, ensure we exclude the page being edited.
                # On add, we only need to check if any other pages with this topic exist
                qs = qs.exclude(pk=self.pk)

            if qs.exists():
                raise ValidationError({"topic": _("This topic is already linked to another theme or topic page.")})


class GenericTaxonomyMixin(models.Model):
    """Generic Taxonomy mixin allows pages to be tagged with one or more topics non-exclusively."""

    taxonomy_panels: ClassVar[list["Panel"]] = [
        MultipleChooserPanel("topics", label=_("Topics"), chooser_field_name=_("topic")),
    ]

    class Meta:
        abstract = True
