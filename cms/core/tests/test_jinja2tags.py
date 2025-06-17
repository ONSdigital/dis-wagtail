from datetime import datetime

from django.template import engines
from django.test import SimpleTestCase
from django.utils.translation import override


class OnsDateFilterInJinjaTests(SimpleTestCase):
    """Integration: ensure the *ons_date* filter is registered in Jinja and
    produces the expected output with the real en-GB `formats.py` constants.
    """

    jinja_env = engines["jinja2"].env

    @classmethod
    def _render(cls, tpl: str, **ctx) -> str:
        return cls.jinja_env.from_string(tpl).render(ctx).strip()

    def test_datetime_format(self):
        """DATETIME_FORMAT = "j F Y g:ia"   →   '1 November 2025 1:00pm'."""
        dt = datetime(2025, 11, 1, 13, 0)  # 1 Nov 2025 13:00
        rendered = self._render(
            "{{ ts|ons_date('DATETIME_FORMAT') }}",
            ts=dt,
        )
        self.assertEqual(rendered, "1 November 2025 1:00pm")

    def test_datetime_format_welsh_typo(self):
        """Test the Welsh translation typo for 'July'."""
        dt = datetime(2025, 7, 1, 13, 0)  # 1 Jul 2025 13:00

        with override("cy"):
            rendered = self._render(
                "{{ ts|ons_date('DATETIME_FORMAT') }}",
                ts=dt,
            )
        self.assertIn("Gorffennaf", rendered, msg="Expected 'Gorffenaf' to be corrected to 'Gorffennaf'.")
