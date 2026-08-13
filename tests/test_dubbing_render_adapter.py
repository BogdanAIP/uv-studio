from __future__ import annotations

import unittest
from dataclasses import dataclass
from unittest import mock

from uv_studio.capabilities import CostClass, LocalityClass, OfferAvailability, build_builtin_capability_registry
from uv_studio.capabilities.adapters.dubbing_render import (
    _audio_filter_graph,
    _ranges_overlap,
    _source_to_master_time_us,
)


@dataclass(frozen=True)
class _VisualEdit:
    start_us: int
    end_us: int

    @property
    def duration_us(self) -> int:
        return self.end_us - self.start_us


@dataclass(frozen=True)
class _DubbingEdit:
    accepted_id: str


class DubbingRenderAdapterTests(unittest.TestCase):
    def test_registry_exposes_local_free_dubbing_render_only_when_ffmpeg_and_ffprobe_exist(self) -> None:
        patch_target = "uv_studio.capabilities.adapters.dubbing_render.shutil.which"
        with mock.patch(patch_target, side_effect=lambda tool: f"/tools/{tool}"):
            offer = next(
                item
                for item in build_builtin_capability_registry().offers_for("video.render_dubbing")
                if item.offer_id == "local_ffmpeg.video_render_dubbing"
            )
        self.assertEqual(offer.availability, OfferAvailability.AVAILABLE)
        self.assertEqual(offer.locality, LocalityClass.LOCAL)
        self.assertEqual(offer.cost_class, CostClass.FREE)
        self.assertIn("audio.replace_range", offer.features)

        with mock.patch(
            patch_target,
            side_effect=lambda tool: "/tools/ffmpeg" if tool == "ffmpeg" else None,
        ):
            missing_probe = next(
                item
                for item in build_builtin_capability_registry().offers_for("video.render_dubbing")
                if item.offer_id == "local_ffmpeg.video_render_dubbing"
            )
        self.assertEqual(missing_probe.availability, OfferAvailability.UNAVAILABLE)
        self.assertIn("ffprobe", missing_probe.reason)

    def test_source_time_mapping_accumulates_only_preceding_visual_duration_deltas(self) -> None:
        edits = (
            _VisualEdit(start_us=1_000_000, end_us=2_000_000),
            _VisualEdit(start_us=5_000_000, end_us=6_000_000),
        )
        replacement_durations = (1_200_000, 800_000)
        self.assertEqual(
            _source_to_master_time_us(500_000, edits, replacement_durations),
            500_000,
        )
        self.assertEqual(
            _source_to_master_time_us(3_000_000, edits, replacement_durations),
            3_200_000,
        )
        self.assertEqual(
            _source_to_master_time_us(7_000_000, edits, replacement_durations),
            7_000_000,
        )

    def test_half_open_overlap_semantics_allow_adjacent_visual_and_dubbing_ranges(self) -> None:
        self.assertTrue(_ranges_overlap(1_000_000, 2_000_000, 1_500_000, 3_000_000))
        self.assertFalse(_ranges_overlap(1_000_000, 2_000_000, 2_000_000, 3_000_000))
        self.assertFalse(_ranges_overlap(2_000_000, 3_000_000, 1_000_000, 2_000_000))

    def test_audio_filter_replaces_exact_ranges_and_pads_short_speech_without_changing_timeline(self) -> None:
        edits = (
            (_DubbingEdit("d1"), 1_000_000, 2_000_000),
            (_DubbingEdit("d2"), 3_000_000, 4_500_000),
        )
        graph = _audio_filter_graph(
            mapped_edits=edits,
            master_duration_us=6_000_000,
            has_source_audio=True,
            sample_rate=48_000,
            channel_layout="stereo",
        )
        self.assertIn("[0:a:0]atrim=start=0us:end=1000000us", graph)
        self.assertIn("[1:a:0]aresample=48000", graph)
        self.assertIn("apad,atrim=duration=1000000us", graph)
        self.assertIn("[2:a:0]aresample=48000", graph)
        self.assertIn("apad,atrim=duration=1500000us", graph)
        self.assertIn("atrim=start=4500000us:end=6000000us", graph)
        self.assertIn("concat=n=5:v=0:a=1[aout]", graph)

    def test_audio_filter_can_create_silence_outside_dubbing_when_source_has_no_audio(self) -> None:
        graph = _audio_filter_graph(
            mapped_edits=((_DubbingEdit("d1"), 1_000_000, 2_000_000),),
            master_duration_us=3_000_000,
            has_source_audio=False,
            sample_rate=48_000,
            channel_layout="stereo",
        )
        self.assertEqual(graph.count("anullsrc=r=48000:cl=stereo"), 2)
        self.assertIn("[1:a:0]aresample=48000", graph)
        self.assertIn("concat=n=3:v=0:a=1[aout]", graph)


if __name__ == "__main__":
    unittest.main()
