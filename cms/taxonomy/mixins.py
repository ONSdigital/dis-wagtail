from typing import ClassVar

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from wagtail.admin.panels import MultipleChooserPanel, Panel

from cms.taxonomy.models import Topic
from cms.taxonomy.panels import ExclusiveTaxonomyFieldPanel
from cms.taxonomy.viewsets import ExclusiveTopicChooserWidget


class ExclusiveTaxonomyMixin(models.Model):
    """A mixin that allows pages to be linked exclusively to a topic."""

    # Note that this is intended to behave as a one-to-one relationship, but multilingual versions of the same page
    # will need to be linked to the same topic, so we need to use a ForeignKey and enforce exclusivity separately
    topic = models.ForeignKey(Topic, on_delete=models.SET_NULL, related_name="related_%(class)s", null=True)

    taxonomy_panels: ClassVar[list[Panel]] = [
        ExclusiveTaxonomyFieldPanel("topic", widget=ExclusiveTopicChooserWidget),
    ]

    class Meta:
        abstract = True

    def clean(self) -> None:
        super().clean()

        if not self.topic_id:
            raise ValidationError({"topic": "A topic is required."})

        if not settings.ENFORCE_EXCLUSIVE_TAXONOMY:
            return

        for exclusive_sub_page_type in ExclusiveTaxonomyMixin.__subclasses__():
            # Check if other pages are exclusively linked to this topic.
            # Translations of the same page are allowed, but other pages aren't.
            qs = exclusive_sub_page_type.objects.filter(  # type: ignore[attr-defined]
                topic=self.topic_id,
                locale=self.locale_id,  # type: ignore[attr-defined]
            )
            if not self._state.adding:
                # On edit, ensure we exclude the page being edited.
                # On add, we only need to check if any other pages with this topic exist
                qs = qs.exclude(pk=self.pk)

            if qs.exists():
                raise ValidationError({"topic": "This topic is already linked to another theme or topic page."})

        # Check if the default locale version of the page has a different topic.
        default_locale_page_with_different_topic = (
            self.get_translations()  # type: ignore[attr-defined]
            .filter(locale__language_code=settings.LANGUAGE_CODE)
            .exclude(topic_id=self.topic_id)
            .exists()
        )
        if default_locale_page_with_different_topic:
            raise ValidationError({"topic": "The topic needs to be the same as the English page."})


class GenericTaxonomyMixin(models.Model):
    """Generic Taxonomy mixin allows pages to be tagged with one or more topics non-exclusively."""

    taxonomy_panels: ClassVar[list[Panel]] = [
        MultipleChooserPanel("topics", label="Topics", chooser_field_name="topic"),
    ]

    class Meta:
        abstract = True

    @property
    def topic_ids(self) -> list[str]:
        """Returns a list of topic IDs associated with the page."""
        return list(self.topics.values_list("topic_id", flat=True)) if hasattr(self, "topics") else []
