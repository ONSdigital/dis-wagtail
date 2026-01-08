from django.test import SimpleTestCase

from cms.bundles.enums import BundleContentItemState


class BundleContentItemStateTestCase(SimpleTestCase):
    """Tests for BundleContentItemState enum."""

    def test_case_insensitive_comparison_with_uppercase(self):
        """Test that enum comparison is case-insensitive with uppercase strings."""
        self.assertEqual(BundleContentItemState.PUBLISHED, "PUBLISHED")
        self.assertEqual("PUBLISHED", BundleContentItemState.PUBLISHED)

    def test_case_insensitive_comparison_with_lowercase(self):
        """Test that enum comparison is case-insensitive with lowercase strings."""
        self.assertEqual(BundleContentItemState.PUBLISHED, "published")
        self.assertEqual("published", BundleContentItemState.PUBLISHED)

    def test_case_insensitive_comparison_with_mixed_case(self):
        """Test that enum comparison is case-insensitive with mixed case strings."""
        self.assertEqual(BundleContentItemState.PUBLISHED, "Published")
        self.assertEqual("PuBlIsHeD", BundleContentItemState.PUBLISHED)

    def test_case_insensitive_comparison_approved(self):
        """Test that case-insensitive comparison works for APPROVED state."""
        self.assertEqual(BundleContentItemState.APPROVED, "approved")
        self.assertEqual("APPROVED", BundleContentItemState.APPROVED)
        self.assertEqual("Approved", BundleContentItemState.APPROVED)

    def test_comparison_with_wrong_value_returns_false(self):
        """Test that comparison with different enum value returns False."""
        self.assertNotEqual(BundleContentItemState.PUBLISHED, "APPROVED")
        self.assertNotEqual(BundleContentItemState.APPROVED, "published")

    def test_comparison_with_enum_values(self):
        """Test that enum-to-enum comparison still works correctly."""
        self.assertEqual(BundleContentItemState.PUBLISHED, BundleContentItemState.PUBLISHED)
        self.assertNotEqual(BundleContentItemState.PUBLISHED, BundleContentItemState.APPROVED)

    def test_comparison_symmetry(self):
        """Test that comparison works symmetrically (str == enum and enum == str)."""
        state_str = "published"
        # Both directions should work
        self.assertTrue(state_str == BundleContentItemState.PUBLISHED)
        self.assertTrue(BundleContentItemState.PUBLISHED == state_str)  # noqa: SIM300
