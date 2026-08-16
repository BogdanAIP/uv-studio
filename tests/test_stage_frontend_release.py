from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.stage_frontend_release import FrontendStageError, stage_frontend


class StageFrontendReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.frontend = self.root / "frontend"
        standalone = self.frontend / ".next" / "standalone"
        standalone.mkdir(parents=True)
        (standalone / "server.js").write_text("console.log('server')\n", encoding="utf-8")
        traced = standalone / "node_modules" / "next"
        traced.mkdir(parents=True)
        (traced / "package.json").write_text("{}\n", encoding="utf-8")
        static = self.frontend / ".next" / "static" / "chunks"
        static.mkdir(parents=True)
        (static / "app.js").write_text("chunk\n", encoding="utf-8")
        public = self.frontend / "public"
        public.mkdir()
        (public / "icon.svg").write_text("<svg/>\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_stage_copies_standalone_static_and_public(self) -> None:
        output = self.root / "staged"
        result = stage_frontend(self.frontend, output)
        self.assertTrue(result["ok"])
        self.assertEqual(result["entrypoint"], "server.js")
        self.assertTrue((output / "server.js").is_file())
        self.assertTrue((output / "node_modules" / "next" / "package.json").is_file())
        self.assertTrue((output / ".next" / "static" / "chunks" / "app.js").is_file())
        self.assertTrue((output / "public" / "icon.svg").is_file())
        self.assertGreaterEqual(result["file_count"], 4)

    def test_stage_supports_frontend_without_public_directory(self) -> None:
        for child in (self.frontend / "public").iterdir():
            child.unlink()
        (self.frontend / "public").rmdir()
        output = self.root / "staged-no-public"
        result = stage_frontend(self.frontend, output)
        self.assertFalse(result["has_public"])
        self.assertTrue(result["has_static"])

    def test_existing_output_is_rejected_instead_of_merged(self) -> None:
        output = self.root / "staged"
        output.mkdir()
        (output / "stale.js").write_text("stale", encoding="utf-8")
        with self.assertRaises(FrontendStageError):
            stage_frontend(self.frontend, output)
        self.assertTrue((output / "stale.js").is_file())

    def test_missing_server_or_static_fails_closed(self) -> None:
        (self.frontend / ".next" / "standalone" / "server.js").unlink()
        with self.assertRaises(FrontendStageError):
            stage_frontend(self.frontend, self.root / "missing-server")

        (self.frontend / ".next" / "standalone" / "server.js").write_text("server\n", encoding="utf-8")
        for path in sorted((self.frontend / ".next" / "static").rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        (self.frontend / ".next" / "static").rmdir()
        with self.assertRaises(FrontendStageError):
            stage_frontend(self.frontend, self.root / "missing-static")


if __name__ == "__main__":
    unittest.main()
