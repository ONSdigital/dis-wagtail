import uuid
from typing import TYPE_CHECKING, Any, ClassVar, Optional

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.forms import Media
from django.utils.functional import cached_property, classproperty
from django.utils.text import capfirst
from django.utils.translation import gettext_lazy as _
from modelcluster.models import ClusterableModel
from wagtail.fields import RichTextField
from wagtail.models import (
    CollectionMember,
    PreviewableMixin,
    SpecificMixin,
)
from wagtail.permission_policies.collections import CollectionOwnershipPermissionPolicy
from wagtail.search import index

if TYPE_CHECKING:
    from django.http import HttpRequest


class Visualisation(
    CollectionMember,
    PreviewableMixin,
    SpecificMixin,
    index.Indexed,
    ClusterableModel,
):
    preview_template: ClassVar[str] = "templates/datavis/preview.html"
    template: ClassVar[str | None] = None
    is_creatable: ClassVar[bool] = False

    uuid = models.UUIDField(  # type: ignore[var-annotated]
        verbose_name=_("UUID"),
        default=uuid.uuid4,
        db_index=True,
        unique=True,
        editable=False,
    )
    name = models.CharField(  # type: ignore[var-annotated]
        verbose_name=_("name"),
        max_length=255,
        help_text=_("The editor-facing name that will appear in the listing and chooser interfaces."),
    )
    content_type = models.ForeignKey(  # type: ignore[var-annotated]
        ContentType,
        verbose_name=_("content type"),
        related_name="charts",
        on_delete=models.CASCADE,
    )
    content_type.wagtail_reference_index_ignore = True  # type: ignore[attr-defined]
    primary_data_source = models.ForeignKey(  # type: ignore[var-annotated]
        "datavis.DataSource",
        verbose_name=_("primary data source"),
        on_delete=models.PROTECT,
    )

    title = models.CharField(  # type: ignore[var-annotated]
        verbose_name=_("title (default)"),
        max_length=255,
        blank=True,
        help_text=_("This will usually be overridden wherever the visualisation is embedded on a page."),
    )
    subtitle = models.CharField(  # type: ignore[var-annotated]
        verbose_name=_("subtitle (default)"),
        max_length=255,
        blank=True,
        help_text=_("This will usually be overridden wherever the visualisation is embedded on a page."),
    )
    caption = RichTextField(
        verbose_name=_("caption"),
        blank=True,
        features=settings.RICH_TEXT_BASIC,
        default="Source: Office for National Statistics",
    )
    created_at = models.DateTimeField(  # type: ignore[var-annotated]
        verbose_name=_("created at"), auto_now_add=True, db_index=True
    )
    last_updated_at = models.DateTimeField(  # type: ignore[var-annotated]
        verbose_name=_("last updated at"), auto_now=True, db_index=True
    )
    created_by = models.ForeignKey(  # type: ignore[var-annotated]
        settings.AUTH_USER_MODEL,
        verbose_name=_("created by"),
        null=True,
        blank=True,
        editable=False,
        on_delete=models.SET_NULL,
        related_name="created_visualisations",
    )
    created_by.wagtail_reference_index_ignore = True  # type: ignore[attr-defined]

    search_fields: ClassVar[list[index.SearchField]] = [
        index.AutocompleteField("name"),
        index.AutocompleteField("title"),
        index.AutocompleteField("subtitle"),
        index.AutocompleteField("caption"),
        index.AutocompleteField("type_label"),
        index.SearchField("name", boost=5),
        index.SearchField("title", boost=1),
        index.SearchField("subtitle"),
        index.SearchField("caption"),
        index.SearchField("type_label"),
        index.FilterField("content_type"),
        index.FilterField("collection"),
        index.FilterField("created_by"),
        index.FilterField("created_at"),
        index.FilterField("last_updated_at"),
    ]

    @classproperty
    def permission_policy(cls) -> "CollectionOwnershipPermissionPolicy":  # pylint: disable=no-self-argument
        return CollectionOwnershipPermissionPolicy(cls, owner_field_name="created_by")

    @cached_property
    def media(self) -> Media:
        return Media()

    def __str__(self) -> str:
        name: str = self.name
        return name

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if not self.id and not self.content_type_id:
            # this model is being newly created
            # rather than retrieved from the db;

            # set content type to correctly represent the model class
            # that this was created as
            self.content_type = ContentType.objects.get_for_model(self, for_concrete_model=False)

    def get_template(self) -> str:
        if self.template is None:
            raise ValueError(
                f"{type(self).__name__}.template is None and the get_template() method has not been overridden."
            )
        return self.template

    def get_context(self, request: Optional["HttpRequest"] = None, **kwargs: Any) -> dict[str, Any]:
        context: dict[str, Any] = {
            "object": self.specific,
            "object_type": self.specific_class,
            "media": self.media,
        }
        context.update(kwargs)
        return context

    def type_label(self) -> str:
        verbose_name: str = self.specific_class._meta.verbose_name
        return capfirst(verbose_name)

    type_label.short_description = _("Type")  # type: ignore[attr-defined]
    type_label.admin_order_field = "content_type__model"  # type: ignore[attr-defined]

    def get_preview_template(self, request: "HttpRequest", mode_name: str, **kwargs: Any) -> str:
        return self.preview_template

    def get_preview_context(self, request: "HttpRequest", mode_name: str, **kwargs: Any) -> dict[str, Any]:
        return self.get_context(request, is_preview=True, **kwargs)
