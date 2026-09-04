import uuid
from unittest.mock import patch

from django.forms import ValidationError
from django.test import TestCase

from cms.articles.models import StatisticalArticlePage
from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.datavis.services import ChartRenderResult
from cms.datavis.tests.factories import RenderedChartImageFactory, TableDataFactory

CONTENT_CHART_ID = "11111111-1111-1111-1111-111111111111"


def chart_block_value():
    return {
        "figure_number": "Figure 1",
        "title": "Test Chart",
        "audio_description": "Description",
        "table": TableDataFactory(),
        "theme": "primary",
        "rendered_chart_image": None,
    }


class ChartRenderOnSubmitTests(TestCase):
    """Covers the workflow trigger: rendering charts when a page is submitted for review."""

    def setUp(self):
        page = StatisticalArticlePageFactory()
        page.content = [
            {
                "type": "section",
                "id": str(uuid.uuid4()),
                "value": {
                    "title": "Section",
                    "content": [{"type": "line_chart", "id": CONTENT_CHART_ID, "value": chart_block_value()}],
                },
            }
        ]
        page.save()
        self.page = StatisticalArticlePage.objects.get(pk=page.pk)
        self.form_class = self.page.get_edit_handler().get_form_class()

    def _build_form(self, *, submitting):
        form = self.form_class(instance=self.page)
        form.data = {"action-submit": "1"} if submitting else {}
        form.cleaned_data = {"content": self.page.content}
        return form

    def test_render_does_not_run_on_a_plain_save(self):
        with patch("cms.core.forms.render_chart_blocks") as mock_render:
            form = self._build_form(submitting=False)
            form.clean()

        mock_render.assert_not_called()

    def test_render_runs_on_submit_and_attaches_the_resulting_image(self):
        image = RenderedChartImageFactory()

        def fake_render(blocks):
            results = []
            for block in blocks:
                block.value["rendered_chart_image"] = image
                results.append(ChartRenderResult(block_id=block.id, changed=True))
            return results

        with patch("cms.core.forms.render_chart_blocks", side_effect=fake_render) as mock_render:
            form = self._build_form(submitting=True)
            form.clean()

        mock_render.assert_called_once()
        content_chart = form.cleaned_data["content"][0].value["content"][0]
        self.assertEqual(content_chart.value["rendered_chart_image"], image)

    def test_render_failure_blocks_submission_with_a_validation_error(self):
        with patch(
            "cms.core.forms.render_chart_blocks",
            return_value=[ChartRenderResult(block_id=CONTENT_CHART_ID, changed=False, error="Something went wrong")],
        ):
            form = self._build_form(submitting=True)
            with self.assertRaises(ValidationError) as ctx:
                form.clean()

        self.assertIn("Something went wrong", ctx.exception.messages)
