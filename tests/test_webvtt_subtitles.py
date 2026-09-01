from __future__ import annotations

import tempfile
import threading
import unittest
import zipfile
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

import uv_studio.projects.archive as project_archive
from uv_studio.capabilities.adapters.webvtt_subtitles import (
    WebVTTSubtitleAdapter,
    _render_webvtt,
)
from uv_studio.capabilities.execution import InvalidCapabilityInput
from uv_studio.capabilities.models import (
    CapabilityOffer,
    CostClass,
    LocalityClass,
    OfferAvailability,
)
from uv_studio.projects.archive import export_project, import_project
from uv_studio.projects.dubbing import DubbingStore, DubbingTranscript, TranscriptSegment
from uv_studio.projects.models import ProjectReference
from uv_studio.projects.store import ProjectStore
from uv_studio.projects.task_records import ProjectTaskRecordStore


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

    def test_webvtt_publication_waits_behind_archive_fence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source_store = ProjectStore(base / "source-projects")
            target_store = ProjectStore(base / "target-projects")
            project = source_store.create_project(
                recipe_id="general_video",
                title="WebVTT publication fence",
                project_id="prj_webvtt_publication",
            )
            project_dir = source_store.project_directory(project.project_id)
            source_path = project_dir / "sources" / "source.mkv"
            source_path.write_bytes(b"webvtt-source")
            source = ProjectReference(
                id="src_webvtt",
                kind="video",
                path="sources/source.mkv",
                metadata={
                    "sha256": "a" * 64,
                    "duration_us": 5_000_000,
                    "has_audio": True,
                },
            )
            source_store.update_project(project.project_id, sources=(source,))
            DubbingStore(source_store).upsert_transcript(
                project.project_id,
                DubbingTranscript(
                    dubbing_id="dub_webvtt",
                    source_id=source.id,
                    source_sha256="a" * 64,
                    language="en",
                    start_us=0,
                    end_us=2_000_000,
                    origin="imported",
                    segments=(
                        TranscriptSegment(
                            segment_id="seg_001",
                            start_us=0,
                            end_us=2_000_000,
                            text="Archive-safe subtitle",
                        ),
                    ),
                ),
            )
            offer = CapabilityOffer(
                "local_webvtt.subtitle_export",
                "subtitle.export_webvtt",
                "local_webvtt",
                "WebVTT test",
                OfferAvailability.AVAILABLE,
                "test",
                LocalityClass.LOCAL,
                CostClass.FREE,
                False,
            )
            adapter = WebVTTSubtitleAdapter(source_store)
            archive_path = base / "before-webvtt.uvproj.zip"
            retry_path = base / "after-webvtt.uvproj.zip"

            schema_sampled = threading.Event()
            release_export = threading.Event()
            publication_started = threading.Event()
            publisher_completed = threading.Event()
            export_errors: list[BaseException] = []
            publisher_errors: list[BaseException] = []
            result_holder: list[object] = []
            original_raw_schema = project_archive._raw_project_schema_version
            real_records = ProjectTaskRecordStore

            def sampled_schema(project_path: Path) -> int:
                version = original_raw_schema(project_path)
                schema_sampled.set()
                if not release_export.wait(timeout=5):
                    raise RuntimeError("test did not release archive snapshot")
                return version

            class ObservedProjectTaskRecordStore:
                def __init__(self, store: ProjectStore) -> None:
                    self.inner = real_records(store)

                @contextmanager
                def project_lock(self, project_id: str):
                    publication_started.set()
                    with self.inner.project_lock(project_id):
                        yield

            def run_export() -> None:
                try:
                    export_project(source_store, project.project_id, archive_path)
                except BaseException as exc:  # pragma: no cover - surfaced below
                    export_errors.append(exc)

            def run_publisher() -> None:
                try:
                    result_holder.append(
                        adapter.execute(
                            project_id=project.project_id,
                            offer=offer,
                            payload={"dubbing_id": "dub_webvtt"},
                        )
                    )
                except BaseException as exc:  # pragma: no cover - surfaced below
                    publisher_errors.append(exc)
                finally:
                    publisher_completed.set()

            export_thread = threading.Thread(target=run_export, daemon=True)
            publisher_thread = threading.Thread(target=run_publisher, daemon=True)
            with (
                mock.patch(
                    "uv_studio.projects.archive._raw_project_schema_version",
                    side_effect=sampled_schema,
                ),
                mock.patch(
                    "uv_studio.capabilities.adapters.webvtt_subtitles.ProjectTaskRecordStore",
                    ObservedProjectTaskRecordStore,
                ),
            ):
                export_thread.start()
                try:
                    self.assertTrue(schema_sampled.wait(timeout=5))
                    publisher_thread.start()
                    self.assertTrue(publication_started.wait(timeout=5))
                    staged = tuple(source_store.root.glob(".uv-webvtt-*.vtt"))
                    self.assertEqual(len(staged), 1)
                    self.assertNotIn(project_dir, staged[0].parents)
                    self.assertEqual(tuple((project_dir / "artifacts").glob("sub_*.vtt")), ())
                    self.assertFalse(
                        publisher_completed.wait(timeout=0.2),
                        "canonical WebVTT publication must wait behind archive snapshot fence",
                    )
                finally:
                    release_export.set()
                    export_thread.join(timeout=5)
                    publisher_thread.join(timeout=5)

            self.assertFalse(export_thread.is_alive())
            self.assertFalse(publisher_thread.is_alive())
            self.assertEqual(export_errors, [])
            self.assertEqual(publisher_errors, [])
            self.assertEqual(len(result_holder), 1)
            with zipfile.ZipFile(archive_path, "r") as archive:
                self.assertFalse(
                    any(name.startswith("project/artifacts/sub_") for name in archive.namelist())
                )

            current = source_store.load_project(project.project_id)
            subtitle = next(item for item in current.artifacts if item.id.startswith("sub_"))
            final_output = source_store.resolve_project_file(
                project.project_id,
                subtitle.path,
                must_exist=True,
                allowed_roots=("artifacts",),
            )
            expected_bytes = final_output.read_bytes()
            self.assertIn(b"Archive-safe subtitle", expected_bytes)

            export_project(source_store, project.project_id, retry_path)
            imported = import_project(target_store, retry_path)
            imported_subtitle = next(item for item in imported.artifacts if item.id == subtitle.id)
            self.assertEqual(imported_subtitle.path, subtitle.path)
            imported_output = target_store.resolve_project_file(
                imported.project_id,
                imported_subtitle.path,
                must_exist=True,
                allowed_roots=("artifacts",),
            )
            self.assertEqual(imported_output.read_bytes(), expected_bytes)


if __name__ == "__main__":
    unittest.main()
