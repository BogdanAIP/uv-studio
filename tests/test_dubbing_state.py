from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from uv_studio.projects.dubbing import (
    DUBBING_STATE_PATH,
    DubbingError,
    DubbingState,
    DubbingStore,
    DubbingTranscript,
    DubbingTranslation,
    TranscriptSegment,
    TranslationSegment,
)
from uv_studio.projects.models import ProjectReference
from uv_studio.projects.store import ProjectStore


SOURCE_SHA256 = "a" * 64


class DubbingStateTests(unittest.TestCase):
    def _project(self, root: Path) -> tuple[ProjectStore, str]:
        store = ProjectStore(root / "projects")
        project = store.create_project(recipe_id="general_video", title="Dubbing test")
        source_path = store.project_directory(project.project_id) / "sources" / "source.mkv"
        source_path.write_bytes(b"project-owned-source")
        source = ProjectReference(
            id="src_video",
            kind="video",
            path="sources/source.mkv",
            metadata={
                "sha256": SOURCE_SHA256,
                "duration_us": 10_000_000,
                "has_audio": True,
            },
        )
        store.update_project(project.project_id, sources=(source,))
        return store, project.project_id

    @staticmethod
    def _transcript(*, text: str = "Hello world") -> DubbingTranscript:
        return DubbingTranscript(
            dubbing_id="dub_main",
            source_id="src_video",
            source_sha256=SOURCE_SHA256,
            language="en-US",
            start_us=1_000_000,
            end_us=6_000_000,
            origin="imported",
            segments=(
                TranscriptSegment(
                    segment_id="seg_001",
                    start_us=1_000_000,
                    end_us=2_500_000,
                    text=text,
                    speaker_label="Speaker 1",
                ),
                TranscriptSegment(
                    segment_id="seg_002",
                    start_us=3_000_000,
                    end_us=5_500_000,
                    text="Second sentence",
                ),
            ),
        )

    @staticmethod
    def _translation(transcript: DubbingTranscript) -> DubbingTranslation:
        return DubbingTranslation(
            translation_id="translation_ru",
            dubbing_id=transcript.dubbing_id,
            transcript_sha256=transcript.digest,
            target_language="ru",
            segments=(
                TranslationSegment(segment_id="seg_001", text="Привет, мир"),
                TranslationSegment(segment_id="seg_002", text="Второе предложение"),
            ),
        )

    def test_roundtrip_persists_provider_neutral_state_under_timeline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store, project_id = self._project(Path(tmp))
            dubbing = DubbingStore(store)
            transcript = self._transcript()

            state = dubbing.upsert_transcript(project_id, transcript)
            state = dubbing.upsert_translation(project_id, self._translation(transcript))

            self.assertEqual(len(state.transcripts), 1)
            self.assertEqual(len(state.translations), 1)
            self.assertEqual(state.transcripts[0].language, "en-us")
            self.assertEqual(state.translations[0].target_language, "ru")

            state_path = store.project_directory(project_id) / DUBBING_STATE_PATH
            self.assertTrue(state_path.is_file())
            payload = json.loads(state_path.read_text(encoding="utf-8"))
            serialized = json.dumps(payload, ensure_ascii=False)
            self.assertNotIn("provider", serialized.lower())
            self.assertNotIn("offer_id", serialized)
            self.assertNotIn(str(store.root), serialized)

            reloaded = dubbing.validate_project(project_id)
            self.assertEqual(reloaded.to_dict(), state.to_dict())

    def test_state_requires_translation_to_cover_exact_transcript_revision(self) -> None:
        transcript = self._transcript()
        incomplete = DubbingTranslation(
            translation_id="translation_ru",
            dubbing_id=transcript.dubbing_id,
            transcript_sha256=transcript.digest,
            target_language="ru",
            segments=(TranslationSegment(segment_id="seg_001", text="Привет"),),
        )
        with self.assertRaises(DubbingError):
            DubbingState(transcripts=(transcript,), translations=(incomplete,))

    def test_store_rejects_translation_with_missing_segment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store, project_id = self._project(Path(tmp))
            dubbing = DubbingStore(store)
            transcript = self._transcript()
            dubbing.upsert_transcript(project_id, transcript)
            incomplete = DubbingTranslation(
                translation_id="translation_ru",
                dubbing_id=transcript.dubbing_id,
                transcript_sha256=transcript.digest,
                target_language="ru",
                segments=(TranslationSegment(segment_id="seg_001", text="Привет"),),
            )
            with self.assertRaises(DubbingError):
                dubbing.upsert_translation(project_id, incomplete)

    def test_store_rejects_transcript_source_revision_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store, project_id = self._project(Path(tmp))
            transcript = DubbingTranscript(
                dubbing_id="dub_main",
                source_id="src_video",
                source_sha256="b" * 64,
                language="en",
                start_us=0,
                end_us=2_000_000,
                origin="asr",
                segments=(
                    TranscriptSegment(
                        segment_id="seg_001",
                        start_us=0,
                        end_us=1_000_000,
                        text="Hello",
                        confidence=0.93,
                    ),
                ),
            )
            with self.assertRaises(DubbingError):
                DubbingStore(store).upsert_transcript(project_id, transcript)

    def test_store_rejects_source_range_past_duration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store, project_id = self._project(Path(tmp))
            transcript = DubbingTranscript(
                dubbing_id="dub_main",
                source_id="src_video",
                source_sha256=SOURCE_SHA256,
                language="en",
                start_us=9_000_000,
                end_us=11_000_000,
                origin="imported",
                segments=(
                    TranscriptSegment(
                        segment_id="seg_001",
                        start_us=9_000_000,
                        end_us=10_500_000,
                        text="Too long",
                    ),
                ),
            )
            with self.assertRaises(DubbingError):
                DubbingStore(store).upsert_transcript(project_id, transcript)

    def test_transcript_change_fails_closed_when_translation_is_bound(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store, project_id = self._project(Path(tmp))
            dubbing = DubbingStore(store)
            transcript = self._transcript()
            dubbing.upsert_transcript(project_id, transcript)
            dubbing.upsert_translation(project_id, self._translation(transcript))

            with self.assertRaises(DubbingError):
                dubbing.upsert_transcript(project_id, self._transcript(text="Changed source text"))

    def test_overlapping_transcript_segments_are_rejected(self) -> None:
        with self.assertRaises(DubbingError):
            DubbingTranscript(
                dubbing_id="dub_main",
                source_id="src_video",
                source_sha256=SOURCE_SHA256,
                language="en",
                start_us=0,
                end_us=5_000_000,
                origin="asr",
                segments=(
                    TranscriptSegment("seg_001", 0, 2_000_000, "One"),
                    TranscriptSegment("seg_002", 1_500_000, 3_000_000, "Two"),
                ),
            )


if __name__ == "__main__":
    unittest.main()
