from typing import TYPE_CHECKING, Any, ClassVar

from django.test import SimpleTestCase

if TYPE_CHECKING:
    from wagtail import blocks


class BaseAnnotationTestCase(SimpleTestCase):
    block_type: ClassVar[type[blocks.StructBlock]]
    raw_data: dict[str, Any]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.block = cls.block_type()

    def get_value(self, raw_data: dict[str, Any] | None = None):
        return self.block.to_python(raw_data)

    def get_config(self, raw_data: dict[str, Any] | None = None):
        value = self.get_value(raw_data)
        return value.get_config()
