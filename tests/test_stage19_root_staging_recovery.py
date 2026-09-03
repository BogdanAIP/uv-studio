from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from uv_studio.generation.recovery import recover_interrupted_generation_jobs
from uv_studio.projects.identity import STUDIO_COMPAT_RECIPE_ID, studio_project_extensions
from uv_studio.projects.store import ProjectStore


class Stage19RootStagingRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.store.create_project(
            title="Root staging recovery",
            recipe_id=STUDIO_COMPAT_RECIPE_ID,
            extensions=studio_project_extensions("micro_drama"),
            project_id="prj_root_staging_recovery",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_startup_reclaims_only_exact_uv_root_staging_files(self) -> None:
        hex_a = "a" * 32
        hex_b = "b" * 32
        hex_c = "c" * 32
        hex_d = "d" * 32

        staging = {
            self.store.root / f".uv-generation-attempt_{hex_a}-deadbeef.png": b"generation",
            self.store.root / f".uv-source-upload-src_{hex_b}.{hex_c}.upload": b"source",
            self.store.root / f".uv-webvtt-sub_{hex_c}-deadbeef.vtt": b"webvtt",
            self.store.root / ".uv-ffconcat-deadbeef.txt": b"ffconcat",
            self.store.root / f".uv-timeline-assemble-art_{hex_d}-deadbeef.mp4": b"timeline",
        }
        for path, payload in staging.items():
            path.write_bytes(payload)

        preserved = {
            self.store.root / ".uv-generation-attempt_nothex-deadbeef.png": b"near-generation",
            self.store.root / f".uv-source-upload-src_{hex_b}.short.upload": b"near-source",
            self.store.root / f".uv-webvtt-art_{hex_c}-deadbeef.vtt": b"near-webvtt",
            self.store.root / ".uv-ffconcat.txt": b"near-ffconcat",
            self.store.root / ".uv-timeline-assemble-art_nothex-deadbeef.mp4": b"near-timeline",
            self.store.root / ".uv-recovered-orphan-prj-anything": b"quarantine",
            self.store.root / "ordinary-root-file.bin": b"ordinary",
        }
        for path, payload in preserved.items():
            path.write_bytes(payload)

        matching_directory = self.store.root / f".uv-generation-attempt_{hex_a}-directory.png"
        matching_directory.mkdir()
        nested = matching_directory / "must-survive.bin"
        nested.write_bytes(b"directory-content")

        self.assertEqual(recover_interrupted_generation_jobs(self.store), ())

        for path in staging:
            self.assertFalse(path.exists(), path.name)
        for path, payload in preserved.items():
            self.assertTrue(path.is_file(), path.name)
            self.assertEqual(path.read_bytes(), payload)
        self.assertTrue(matching_directory.is_dir())
        self.assertEqual(nested.read_bytes(), b"directory-content")
        self.store.load_project("prj_root_staging_recovery")


if __name__ == "__main__":
    unittest.main()
