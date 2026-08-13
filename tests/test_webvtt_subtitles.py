from __future__ import annotations

import unittest

from uv_studio.capabilities.adapters.webvtt_subtitles import _render_webvtt
from uv_studio.capabilities.execution import InvalidCapabilityInput


class WebVTTSubtitleTests(unittest.TestCase):
    def test_render_floors_start_ceils_end_escapes_and_removes_blank_cue_lines(self) -> None:
        result = _render_webvtt(
            (
                ("seg_1", 1_234_567, 2_345_001, "A < B & C\n\nsecond line"),
                ("seg_2", 2_345_001, 2_345_002, "next"),
            )
        )
        self.assertEqual(
            result,
            "WEBVTT\n\n"
            "seg_1\n"
            "00:00:01.234 --> 00:00:02.346\n"
            "A &lt; B &amp; C\nsecond line\n\n"
            "seg_2\n"
            "00:00:02.345 --> 00:00:02.346\n"
            "next\n",
        )

    def test_overlapping_dialogue_is_allowed_but_reverse_or_unsorted_ranges_fail_closed(self) -> None:
        overlapping = _render_webvtt(
            (
                ("speaker_a", 0, 1_500_000, "one"),
                ("speaker_b", 1_000_000, 2_000_000, "two"),
            )
        )
        self.assertIn("speaker_b", overlapping)

        with self.assertRaisesRegex(InvalidCapabilityInput, "non-negative and forward"):
            _render_webvtt((("bad", 1_000_000, 900_000, "bad"),))

        with self.assertRaisesRegex(InvalidCapabilityInput, "non-decreasing start time"):
            _render_webvtt(
                (
                    ("later", 2_000_000, 3_000_000, "later"),
                    ("earlier", 1_000_000, 2_500_000, "earlier"),
                )
            )


if __name__ == "__main__":
    unittest.main()
