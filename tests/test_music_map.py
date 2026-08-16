from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from uv_studio.projects.models import ProjectReference
from uv_studio.projects.music_map import (
    MUSIC_MAP_PATH,
    MusicExcerpt,
    MusicLyricPhrase,
    MusicMapError,
    MusicMapStore,
    MusicSection,
    MusicTimingMarker,
)
from uv_studio.projects.store import ProjectStore


class MusicMapTests(unittest.TestCase):
    def _register_audio(
        self,
        store: ProjectStore,
        project_id: str,
        *,
        reference_id: str = "song",
        filename: str = "song.wav",
        payload: bytes = b"music-map-audio",
        duration_us: int = 30_000_000,
    ) -> ProjectReference:
        project_dir = store.project_directory(project_id)
        path = project_dir / "sources" / filename
        path.write_bytes(payload)
        reference = ProjectReference(
            id=reference_id,
            kind="audio",
            path=f"sources/{filename}",
            metadata={
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": len(payload),
                "duration_us": duration_us,
            },
        )
        project = store.load_project(project_id)
        store.update_project(project_id, sources=(*project.sources, reference))
        return reference

    def _set_valid_map(self, store: ProjectStore, project_id: str):
        service = MusicMapStore(store)
        state = service.set_map(
            project_id,
            song_reference_id="song",
            excerpt=MusicExcerpt(start_us=2_000_000, end_us=27_000_000),
            sections=(
                MusicSection(
                    section_id="chorus",
                    kind="chorus",
                    label="Chorus",
                    start_us=12_000_000,
                    end_us=27_000_000,
                ),
                MusicSection(
                    section_id="verse",
                    kind="verse",
                    label="Verse",
                    start_us=2_000_000,
                    end_us=12_000_000,
                ),
            ),
            markers=(
                MusicTimingMarker(marker_id="beat_2", kind="beat", time_us=8_000_000),
                MusicTimingMarker(marker_id="beat_1", kind="downbeat", time_us=4_000_000),
                MusicTimingMarker(marker_id="peak", kind="climax", time_us=20_000_000),
            ),
            lyric_phrases=(
                MusicLyricPhrase(
                    phrase_id="line_1",
                    start_us=3_000_000,
                    end_us=6_500_000,
                    text="First line",
                ),
            ),
        )
        return service, state

    def test_music_map_is_opt_in_and_revision_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ProjectStore(Path(tmp) / "projects")
            project = store.create_project(title="Music map", recipe_id="music_video")
            self._register_audio(store, project.project_id)

            service = MusicMapStore(store)
            self.assertIsNone(service.load(project.project_id))
            self.assertFalse((store.project_directory(project.project_id) / MUSIC_MAP_PATH).exists())

            service, state = self._set_valid_map(store, project.project_id)
            reopened = service.load(project.project_id, validate_current=True)
            self.assertIsNotNone(reopened)
            assert reopened is not None
            self.assertEqual(reopened.revision_sha256, state.revision_sha256)
            self.assertEqual([item.section_id for item in reopened.sections], ["verse", "chorus"])
            self.assertEqual(
                [item.marker_id for item in reopened.markers],
                ["beat_1", "beat_2", "peak"],
            )
            self.assertEqual(reopened.song.reference_path, "sources/song.wav")
            self.assertEqual(reopened.excerpt.duration_us, 25_000_000)

    def test_map_rejects_out_of_excerpt_and_overlapping_structure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ProjectStore(Path(tmp) / "projects")
            project = store.create_project(title="Music bounds", recipe_id="music_video")
            self._register_audio(store, project.project_id)
            service = MusicMapStore(store)

            with self.assertRaisesRegex(MusicMapError, "must not overlap"):
                service.set_map(
                    project.project_id,
                    song_reference_id="song",
                    excerpt=MusicExcerpt(start_us=0, end_us=20_000_000),
                    sections=(
                        MusicSection(
                            section_id="a",
                            kind="verse",
                            label="A",
                            start_us=0,
                            end_us=11_000_000,
                        ),
                        MusicSection(
                            section_id="b",
                            kind="chorus",
                            label="B",
                            start_us=10_000_000,
                            end_us=20_000_000,
                        ),
                    ),
                )

            with self.assertRaisesRegex(MusicMapError, "half-open excerpt"):
                service.set_map(
                    project.project_id,
                    song_reference_id="song",
                    excerpt=MusicExcerpt(start_us=5_000_000, end_us=15_000_000),
                    markers=(
                        MusicTimingMarker(marker_id="outside", kind="beat", time_us=15_000_000),
                    ),
                )

    def test_current_song_bytes_and_stored_revision_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ProjectStore(Path(tmp) / "projects")
            project = store.create_project(title="Music trust", recipe_id="music_video")
            self._register_audio(store, project.project_id)
            service, _ = self._set_valid_map(store, project.project_id)

            song_path = store.project_directory(project.project_id) / "sources" / "song.wav"
            song_path.write_bytes(b"changed-song-bytes")
            with self.assertRaises(MusicMapError):
                service.load(project.project_id, validate_current=True)

            song_path.write_bytes(b"music-map-audio")
            state_path = store.project_directory(project.project_id) / MUSIC_MAP_PATH
            raw = json.loads(state_path.read_text(encoding="utf-8"))
            raw["sections"][0]["label"] = "Changed without revision refresh"
            state_path.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaisesRegex(MusicMapError, "revision"):
                service.load(project.project_id)

    def test_music_map_requires_project_owned_audio_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ProjectStore(Path(tmp) / "projects")
            project = store.create_project(title="Music reference", recipe_id="music_video")
            project_dir = store.project_directory(project.project_id)
            video_path = project_dir / "sources" / "song.mp4"
            video_path.write_bytes(b"not-audio-reference")
            ref = ProjectReference(
                id="song_video",
                kind="video",
                path="sources/song.mp4",
                metadata={
                    "sha256": hashlib.sha256(b"not-audio-reference").hexdigest(),
                    "size_bytes": len(b"not-audio-reference"),
                    "duration_us": 20_000_000,
                },
            )
            current = store.load_project(project.project_id)
            store.update_project(project.project_id, sources=(*current.sources, ref))
            with self.assertRaisesRegex(MusicMapError, "project-owned audio"):
                MusicMapStore(store).set_map(
                    project.project_id,
                    song_reference_id="song_video",
                    excerpt=MusicExcerpt(start_us=0, end_us=10_000_000),
                )


if __name__ == "__main__":
    unittest.main()
