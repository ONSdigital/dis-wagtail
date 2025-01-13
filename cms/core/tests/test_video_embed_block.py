from django.test import TestCase
from wagtail.blocks import StructBlockValidationError
from wagtail_factories import ImageFactory

from cms.core.blocks import VideoEmbedBlock


class VideoEmbedBlockTestCase(TestCase):
    """Test for video embed block."""

    def setUp(self):
        self.video_block = VideoEmbedBlock()
        self.image = ImageFactory.create()

    def test_videoembedblock_clean__invalid_domain(self):
        """Check the VideoEmbedBlock validates the supplied URL."""
        with self.assertRaises(StructBlockValidationError) as info:
            value = self.video_block.to_python(
                {
                    "link_url": "https://ons.gov.uk/908205163",
                    "image": self.image.id,
                    "title": "The video",
                    "link_text": "Watch the video",
                }
            )
            self.video_block.clean(value)

        self.assertEqual(
            info.exception.block_errors["link_url"].message,
            "The link URL must use a valid vimeo or youtube video URL",
        )

    def test_videoembedblock_clean__invalid_youtube_link_1(self):
        """Check the VideoEmbedBlock validates the supplied URL."""
        with self.assertRaises(StructBlockValidationError) as info:
            value = self.video_block.to_python(
                {
                    "link_url": "https://www.youtube.com/watch/foo?v=ywzZXO-A7Pg",
                    "image": self.image.id,
                    "title": "The video",
                    "link_text": "Watch the video",
                }
            )
            self.video_block.clean(value)

        self.assertEqual(
            info.exception.block_errors["link_url"].message,
            "The link URL must use a valid vimeo or youtube video URL",
        )

    def test_videoembedblock_clean__invalid_youtube_link_2(self):
        """Check the VideoEmbedBlock validates the supplied URL."""
        with self.assertRaises(StructBlockValidationError) as info:
            value = self.video_block.to_python(
                {
                    "link_url": "https://youtu.be/something/ywzZXO-A7Pg",
                    "image": self.image.id,
                    "title": "The video",
                    "link_text": "Watch the video",
                }
            )
            self.video_block.clean(value)

        self.assertEqual(
            info.exception.block_errors["link_url"].message,
            "The link URL must use a valid vimeo or youtube video URL",
        )

    def test_videoembedblock_clean__invalid_youtube_link_3(self):
        """Check the VideoEmbedBlock validates the supplied URL."""
        with self.assertRaises(StructBlockValidationError) as info:
            value = self.video_block.to_python(
                {
                    "link_url": "https://www.youtube.com/v/foo/bar/ywzZXO-A7Pg",
                    "image": self.image.id,
                    "title": "The video",
                    "link_text": "Watch the video",
                }
            )
            self.video_block.clean(value)

        self.assertEqual(
            info.exception.block_errors["link_url"].message,
            "The link URL must use a valid vimeo or youtube video URL",
        )

    def test_videoembedblock_clean__valid_youtube_link_1(self):
        """Check the VideoEmbedBlock validates the supplied URL."""
        value = self.video_block.to_python(
            {
                "link_url": "https://www.youtube.com/watch?v=ywzZXO-A7Pg&foo=bar",
                "image": self.image.id,
                "title": "The video",
                "link_text": "Watch the video",
            }
        )

        self.assertEqual(self.video_block.clean(value), value)

    def test_videoembedblock_clean__valid_youtube_link_2(self):
        """Check the VideoEmbedBlock validates the supplied URL."""
        value = self.video_block.to_python(
            {
                "link_url": "https://youtu.be/ywzZXO-A7Pg",
                "image": self.image.id,
                "title": "The video",
                "link_text": "Watch the video",
            }
        )

        self.assertEqual(self.video_block.clean(value), value)

    def test_videoembedblock_clean__valid_youtube_link_3(self):
        """Check the VideoEmbedBlock validates the supplied URL."""
        value = self.video_block.to_python(
            {
                "link_url": "https://www.youtube.com/v/ywzZXO-A7Pg",
                "image": self.image.id,
                "title": "The video",
                "link_text": "Watch the video",
            }
        )

        self.assertEqual(self.video_block.clean(value), value)

    def test_videoembedblock_clean__invalid_vimeo_link_1(self):
        """Check the VideoEmbedBlock validates the supplied URL."""
        with self.assertRaises(StructBlockValidationError) as info:
            value = self.video_block.to_python(
                {
                    "link_url": "https://vimeo.com/foo/bar/908205163",
                    "image": self.image.id,
                    "title": "The video",
                    "link_text": "Watch the video",
                }
            )
            self.video_block.clean(value)

        self.assertEqual(
            info.exception.block_errors["link_url"].message,
            "The link URL must use a valid vimeo or youtube video URL",
        )

    def test_videoembedblock_clean__invalid_vimeo_link_2(self):
        """Check the VideoEmbedBlock validates the supplied URL."""
        with self.assertRaises(StructBlockValidationError) as info:
            value = self.video_block.to_python(
                {
                    "link_url": "https://player.vimeo.com/video/test/908205163",
                    "image": self.image.id,
                    "title": "The video",
                    "link_text": "Watch the video",
                }
            )
            self.video_block.clean(value)

        self.assertEqual(
            info.exception.block_errors["link_url"].message,
            "The link URL must use a valid vimeo or youtube video URL",
        )

    def test_videoembedblock_clean__invalid_vimeo_link_3(self):
        """Check the VideoEmbedBlock validates the supplied URL."""
        with self.assertRaises(StructBlockValidationError) as info:
            value = self.video_block.to_python(
                {
                    "link_url": "https://vimeo.com/showcase/7934865/foo/493407585",
                    "image": self.image.id,
                    "title": "The video",
                    "link_text": "Watch the video",
                }
            )
            self.video_block.clean(value)

        self.assertEqual(
            info.exception.block_errors["link_url"].message,
            "The link URL must use a valid vimeo or youtube video URL",
        )

    def test_videoembedblock_clean__valid_vimeo_link_1(self):
        """Check the VideoEmbedBlock validates the supplied URL."""
        value = self.video_block.to_python(
            {
                "link_url": "https://vimeo.com/908205163?share=copy",
                "image": self.image.id,
                "title": "The video",
                "link_text": "Watch the video",
            }
        )

        self.assertEqual(self.video_block.clean(value), value)

    def test_videoembedblock_clean__valid_vimeo_link_2(self):
        """Check the VideoEmbedBlock validates the supplied URL."""
        value = self.video_block.to_python(
            {
                "link_url": "https://player.vimeo.com/video/908205163",
                "image": self.image.id,
                "title": "The video",
                "link_text": "Watch the video",
            }
        )

        self.assertEqual(self.video_block.clean(value), value)

    def test_videoembedblock_clean__valid_vimeo_link_3(self):
        """Check the VideoEmbedBlock validates the supplied URL."""
        value = self.video_block.to_python(
            {
                "link_url": "https://vimeo.com/showcase/7934865/video/493407585",
                "image": self.image.id,
                "title": "The video",
                "link_text": "Watch the video",
            }
        )

        self.assertEqual(self.video_block.clean(value), value)
