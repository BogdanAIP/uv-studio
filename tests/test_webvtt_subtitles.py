from __future__ import annotations

import unittest

from uv_studio.capabilities.adapters.webvtt_subtitles import _render_webvtt
from uv_studio.capabilities.execution import InvalidCapabilityInput


class WebVTTSubtitleTests(unittest.TestCase):
    def test_render_floors_start_ceils_end_and_escapes_payload_text(self) -> None:
        result = _render_webvtt(
            (
                ("seg_1", 1_234_567, 2_345_001, "A < B & C"),
                ("seg_2", 2_345_001, 2_345_002, "next"),
            )
        )
        self.assertEqual(
            result,
            "WEBVTT\n\n"
            "seg_1\n"
            "00:00:01.234 --> 00:00:02.346\n"
            "A &lt; B &amp; C\n\n"
            "seg_2\n"
            "00:00:02.345 --> 00:00:02.346\n"
            "next\n",
        )

    def test_adjacent_ranges_are_allowed_but_overlap_fails_closed(self) -> None:
        adjacent = _render_webvtt(
            (
                ("seg_1", 0, 1_000_000, "one"),
                ("seg_2", 1_000_000, 2_000_000, "two"),
            )
        )
        self.assertIn("seg_2", adjacent)

        with self.assertRaisesRegex(InvalidCapabilityInput, "must not overlap"):
            _render_webvtt(
                (
                    ("seg_1", 0, 1_100_000, "one"),
                    ("seg_2", 1_000_000, 2_000_000, "two"),
                )
            )


if __name__ == "__main__":
    unittest.main()
