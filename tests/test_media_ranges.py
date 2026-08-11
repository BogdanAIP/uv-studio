from __future__ import annotations

import unittest

from uv_studio.projects.media_ranges import ProjectMediaRange
from uv_studio.projects.models import ProjectValidationError


class ProjectMediaRangeTests(unittest.TestCase):
    def test_round_trip_uses_integer_microseconds(self) -> None:
        media_range = ProjectMediaRange(
            source_path="sources/input.mp4",
            start_us=5_000_001,
            end_us=10_250_001,
            context_before_us=2_000_000,
            context_after_us=3_000_000,
        )
        self.assertEqual(
            ProjectMediaRange.from_dict(media_range.to_dict()),
            media_range,
        )
        self.assertEqual(media_range.duration_us, 5_250_000)

    def test_requested_range_must_be_positive_and_ordered(self) -> None:
        invalid = (
            {"start_us": -1, "end_us": 1},
            {"start_us": 1, "end_us": 1},
            {"start_us": 2, "end_us": 1},
            {"start_us": True, "end_us": 2},
            {"start_us": 0, "end_us": 1.5},
        )
        for values in invalid:
            with self.subTest(values=values):
                with self.assertRaises(ProjectValidationError):
                    ProjectMediaRange(source_path="sources/input.mp4", **values)

    def test_context_must_be_non_negative_integer_microseconds(self) -> None:
        for field, value in (
            ("context_before_us", -1),
            ("context_after_us", -1),
            ("context_before_us", True),
            ("context_after_us", 0.5),
        ):
            kwargs = {field: value}
            with self.subTest(field=field, value=value):
                with self.assertRaises(ProjectValidationError):
                    ProjectMediaRange(
                        source_path="sources/input.mp4",
                        start_us=1,
                        end_us=2,
                        **kwargs,
                    )

    def test_project_source_path_is_canonical_and_cannot_escape(self) -> None:
        normalized = ProjectMediaRange(
            source_path="sources\\folder\\input.mp4",
            start_us=0,
            end_us=1,
        )
        self.assertEqual(normalized.source_path, "sources/folder/input.mp4")
        for source_path in ("../outside.mp4", "/tmp/outside.mp4", "C:\\outside.mp4"):
            with self.subTest(source_path=source_path):
                with self.assertRaises(ProjectValidationError):
                    ProjectMediaRange(source_path=source_path, start_us=0, end_us=1)

    def test_range_must_fit_real_source_duration(self) -> None:
        media_range = ProjectMediaRange(
            source_path="sources/input.mp4",
            start_us=1_000_000,
            end_us=4_000_001,
        )
        with self.assertRaises(ProjectValidationError):
            media_range.resolve(4_000_000)
        with self.assertRaises(ProjectValidationError):
            media_range.resolve(0)
        with self.assertRaises(ProjectValidationError):
            media_range.resolve(True)

    def test_context_clamps_without_changing_requested_interval(self) -> None:
        media_range = ProjectMediaRange(
            source_path="sources/input.mp4",
            start_us=1_000_000,
            end_us=9_000_000,
            context_before_us=4_000_000,
            context_after_us=4_000_000,
        )
        resolved = media_range.resolve(10_000_000)
        self.assertEqual((resolved.start_us, resolved.end_us), (1_000_000, 9_000_000))
        self.assertEqual((resolved.context_start_us, resolved.context_end_us), (0, 10_000_000))
        self.assertEqual(resolved.before_duration_us, 1_000_000)
        self.assertEqual(resolved.after_duration_us, 1_000_000)
        self.assertEqual(resolved.to_dict()["requested"]["start_us"], 1_000_000)
        self.assertEqual(resolved.to_dict()["requested"]["end_us"], 9_000_000)

    def test_unknown_serialized_fields_and_schema_versions_fail_closed(self) -> None:
        with self.assertRaises(ProjectValidationError):
            ProjectMediaRange.from_dict(
                {
                    "source_path": "sources/input.mp4",
                    "start_us": 0,
                    "end_us": 1,
                    "provider": "should-not-be-here",
                }
            )
        with self.assertRaises(ProjectValidationError):
            ProjectMediaRange.from_dict(
                {
                    "schema_version": 999,
                    "source_path": "sources/input.mp4",
                    "start_us": 0,
                    "end_us": 1,
                }
            )


if __name__ == "__main__":
    unittest.main()
