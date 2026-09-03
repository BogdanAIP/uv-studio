from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from uv_studio.projects.identity import STUDIO_COMPAT_RECIPE_ID, studio_project_extensions
from uv_studio.projects.root_staging import (
    acquire_generation_root_staging,
    recover_stale_root_staging,
    release_root_staging,
)
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

    @staticmethod
    def _lease_path(path: Path) -> Path:
        return path.with_name(f"{path.name}.lease")

    def _make_stale(self, name: str, payload: bytes) -> Path:
        path = self.store.root / name
        path.write_bytes(payload)
        lease = self._lease_path(path)
        lease.write_bytes(b"\0")
        return path

    def test_restart_reclaims_all_exact_stale_names_but_preserves_live_and_unknown_root_state(self) -> None:
        hex_a = "a" * 32
        hex_b = "b" * 32
        hex_c = "c" * 32
        hex_d = "d" * 32
        hex_e = "e" * 32
        token = "f" * 32

        stale = {
            self._make_stale(
                f".uv-generation-attempt_{hex_a}-{token}.png",
                b"generation",
            ),
            self._make_stale(
                f".uv-source-upload-src_{hex_b}.{token}.upload",
                b"source",
            ),
            self._make_stale(
                f".uv-webvtt-sub_{hex_c}-{token}.vtt",
                b"webvtt",
            ),
            self._make_stale(
                f".uv-ffconcat-{token}.txt",
                b"ffconcat",
            ),
            self._make_stale(
                f".uv-timeline-assemble-art_{hex_d}-{token}.mp4",
                b"timeline",
            ),
        }

        sidecar_only = self.store.root / f".uv-ffconcat-{hex_e}.txt.lease"
        sidecar_only.write_bytes(b"\0")

        live = acquire_generation_root_staging(
            self.store.root,
            f"attempt_{hex_e}",
            ".mp4",
        )
        live.write_bytes(b"still-writing")
        live_lease = self._lease_path(live)

        preserved = {
            self.store.root / f".uv-generation-attempt_{hex_a}-{token}.png.unleased": b"near-generation",
            self.store.root / f".uv-source-upload-src_{hex_b}.short.upload": b"near-source",
            self.store.root / f".uv-webvtt-art_{hex_c}-{token}.vtt": b"near-webvtt",
            self.store.root / ".uv-ffconcat.txt": b"near-ffconcat",
            self.store.root / f".uv-timeline-assemble-art_nothex-{token}.mp4": b"near-timeline",
            self.store.root / ".uv-recovered-orphan-prj-anything": b"quarantine",
            self.store.root / "ordinary-root-file.bin": b"ordinary",
        }
        for path, payload in preserved.items():
            path.write_bytes(payload)

        # Exact current-format bytes without a lease are intentionally preserved:
        # an older cooperating runtime may still be writing them and cannot prove
        # liveness through the new lease protocol.
        unleased_exact = self.store.root / f".uv-generation-attempt_{hex_b}-{hex_c}.wav"
        unleased_exact.write_bytes(b"legacy-unleased")

        matching_directory = self.store.root / f".uv-generation-attempt_{hex_c}-{hex_d}.png"
        matching_directory.mkdir()
        nested = matching_directory / "must-survive.bin"
        nested.write_bytes(b"directory-content")
        directory_lease = self._lease_path(matching_directory)
        directory_lease.write_bytes(b"\0")

        try:
            recovered = set(recover_stale_root_staging(self.store.root))

            self.assertEqual(recovered, stale)
            for path in stale:
                self.assertFalse(path.exists(), path.name)
                self.assertFalse(self._lease_path(path).exists(), path.name)
            self.assertFalse(sidecar_only.exists())

            self.assertTrue(live.is_file())
            self.assertEqual(live.read_bytes(), b"still-writing")
            self.assertTrue(live_lease.is_file())

            self.assertTrue(unleased_exact.is_file())
            self.assertEqual(unleased_exact.read_bytes(), b"legacy-unleased")
            for path, payload in preserved.items():
                self.assertTrue(path.is_file(), path.name)
                self.assertEqual(path.read_bytes(), payload)
            self.assertTrue(matching_directory.is_dir())
            self.assertTrue(directory_lease.is_file())
            self.assertEqual(nested.read_bytes(), b"directory-content")
            self.store.load_project("prj_root_staging_recovery")
        finally:
            release_root_staging(live)

        self.assertFalse(live.exists())
        self.assertFalse(live_lease.exists())

    def test_application_lifespan_reclaims_root_staging_before_project_recovery(self) -> None:
        from uv_studio import server as server_module

        calls: list[tuple[str, object]] = []

        def root_recovery(root: Path) -> tuple[Path, ...]:
            calls.append(("root", root))
            return ()

        def project_recovery(store: ProjectStore) -> tuple[str, ...]:
            calls.append(("project", store))
            return ()

        async def exercise() -> None:
            with (
                patch.object(server_module, "get_project_store", return_value=self.store),
                patch.object(server_module, "recover_stale_root_staging", side_effect=root_recovery),
                patch.object(
                    server_module,
                    "recover_interrupted_generation_jobs",
                    side_effect=project_recovery,
                ),
            ):
                async with server_module.lifespan(server_module.app):
                    pass

        asyncio.run(exercise())
        self.assertEqual(
            calls,
            [
                ("root", self.store.root),
                ("project", self.store),
            ],
        )


if __name__ == "__main__":
    unittest.main()
