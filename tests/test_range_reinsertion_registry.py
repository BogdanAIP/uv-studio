from __future__ import annotations

import unittest
from unittest import mock

from uv_studio.capabilities import (
    CostClass,
    LocalityClass,
    OfferAvailability,
    build_builtin_capability_registry,
)


class RangeReinsertionRegistryTests(unittest.TestCase):
    def test_replace_range_offer_requires_ffmpeg_and_ffprobe_and_stays_local_free(self) -> None:
        patch_target = "uv_studio.capabilities.builtin.shutil.which"
        with mock.patch(
            patch_target,
            side_effect=lambda tool: f"/tools/{tool}" if tool == "ffmpeg" else None,
        ):
            missing_probe = next(
                item
                for item in build_builtin_capability_registry().offers_for("video.replace_range")
                if item.offer_id == "local_ffmpeg.video_replace_range"
            )
        self.assertEqual(missing_probe.availability, OfferAvailability.UNAVAILABLE)
        self.assertIn("ffprobe", missing_probe.reason)

        with mock.patch(patch_target, side_effect=lambda tool: f"/tools/{tool}"):
            available = next(
                item
                for item in build_builtin_capability_registry().offers_for("video.replace_range")
                if item.offer_id == "local_ffmpeg.video_replace_range"
            )
        self.assertEqual(available.availability, OfferAvailability.AVAILABLE)
        self.assertEqual(available.locality, LocalityClass.LOCAL)
        self.assertEqual(available.cost_class, CostClass.FREE)
        self.assertFalse(available.asynchronous)
        self.assertIn("video.range_replace", available.features)
        self.assertIn("video.reinsertion", available.features)


if __name__ == "__main__":
    unittest.main()
