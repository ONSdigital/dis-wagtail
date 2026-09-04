import copy
import uuid

from django.test import TestCase
from wagtail.blocks.stream_block import StreamValue

from cms.articles.models import StatisticalArticlePage
from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.datavis.tests.factories import RenderedChartImageFactory, TableDataFactory

CONTENT_CHART_ID = "11111111-1111-1111-1111-111111111111"
FEATURED_CHART_ID = "22222222-2222-2222-2222-222222222222"


def chart_block_value(image_pk):
    return {
        "figure_number": "Figure 1",
        "title": "Test Chart",
        "audio_description": "Description",
        "table": TableDataFactory(),
        "theme": "primary",
        "rendered_chart_image": image_pk,
    }


class TamperProtectionTests(TestCase):
    def setUp(self):
        self.persisted = RenderedChartImageFactory()
        self.forged = RenderedChartImageFactory()

        page = StatisticalArticlePageFactory()
        page.content = [
            {
                "type": "section",
                "id": str(uuid.uuid4()),
                "value": {
                    "title": "Section",
                    "content": [
                        {
                            "type": "line_chart",
                            "id": CONTENT_CHART_ID,
                            "value": chart_block_value(self.persisted.pk),
                        }
                    ],
                },
            }
        ]
        page.featured_chart = [
            {"type": "line_chart", "id": FEATURED_CHART_ID, "value": chart_block_value(self.persisted.pk)}
        ]
        page.save()

        self.page = StatisticalArticlePage.objects.get(pk=page.pk)
        self.form_class = self.page.get_edit_handler().get_form_class()

    def _submitted_stream(self, field_name, *, image_pk, block_id=None):
        """Build an independent stream for the field, with the given image id forced onto charts."""
        original = getattr(self.page, field_name)
        raw = copy.deepcopy(original.get_prep_value())
        for block in raw:
            charts = block["value"]["content"] if block["type"] == "section" else [block]
            for chart in charts:
                chart["value"]["rendered_chart_image"] = image_pk
                if block_id is not None:
                    chart["id"] = block_id
        return StreamValue(original.stream_block, raw, is_lazy=True)

    def test_forged_ids_are_replaced_with_persisted_values(self):
        form = self.form_class(instance=self.page)
        form.cleaned_data = {
            "content": self._submitted_stream("content", image_pk=self.forged.pk),
            "featured_chart": self._submitted_stream("featured_chart", image_pk=self.forged.pk),
        }

        form.clean()

        content_chart = form.cleaned_data["content"][0].value["content"][0]
        featured_chart = form.cleaned_data["featured_chart"][0]

        self.assertEqual(content_chart.value["rendered_chart_image"], self.persisted)
        self.assertEqual(featured_chart.value["rendered_chart_image"], self.persisted)

    def test_image_on_block_with_no_persisted_match_is_cleared(self):
        form = self.form_class(instance=self.page)
        form.cleaned_data = {
            "featured_chart": self._submitted_stream(
                "featured_chart", image_pk=self.forged.pk, block_id=str(uuid.uuid4())
            )
        }

        form.clean()

        self.assertIsNone(form.cleaned_data["featured_chart"][0].value["rendered_chart_image"])
