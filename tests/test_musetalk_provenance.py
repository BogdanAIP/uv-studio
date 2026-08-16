from __future__ import annotations

import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from uv_studio.capabilities.adapters.musetalk import MUSE_TALK_UPSTREAM_COMMIT
from uv_studio.capabilities.adapters.musetalk_verified import (
    MUSE_TALK_INFERENCE_BLOB_SHA1,
    MuseTalkAdapter,
    _PINNED_MODEL_SHA256,
    _checkout_problem,
    _git_blob_sha1,
    _model_payload_problem,
    _runtime_code_path,
    _runtime_path_is_untrusted,
    _runtime_problem,
    _sha256_file,
)


class MuseTalkProvenanceTests(unittest.TestCase):
    @staticmethod
    def _runner(
        *,
        head: str,
        dirty: str = "",
        untracked: str = "",
        ignored: str = "",
    ):
        def run(command, **kwargs):
            if "rev-parse" in command:
                return subprocess.CompletedProcess(command, 0, head + "\n", "")
            if "status" in command:
                return subprocess.CompletedProcess(command, 0, dirty, "")
            if "ls-files" in command:
                payload = ignored if "--ignored" in command else untracked
                return subprocess.CompletedProcess(command, 0, payload, "")
            raise AssertionError(command)
        return run

    def test_wrong_or_dirty_checkout_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir()
            (root / "scripts" / "inference.py").write_bytes(b"placeholder")
            with mock.patch(
                "uv_studio.capabilities.adapters.musetalk_verified._git_blob_sha1",
                return_value=MUSE_TALK_INFERENCE_BLOB_SHA1,
            ):
                wrong = _checkout_problem(
                    root,
                    runner=self._runner(head="0" * 40),
                    git_path="git",
                )
                dirty = _checkout_problem(
                    root,
                    runner=self._runner(head=MUSE_TALK_UPSTREAM_COMMIT, dirty=" M scripts/inference.py\n"),
                    git_path="git",
                )
        self.assertIn("pinned", wrong or "")
        self.assertIn("clean", dirty or "")

    def test_exact_clean_checkout_also_requires_pinned_inference_blob(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir()
            inference = root / "scripts" / "inference.py"
            inference.write_bytes(b"different inference")
            mismatch = _checkout_problem(
                root,
                runner=self._runner(head=MUSE_TALK_UPSTREAM_COMMIT),
                git_path="git",
            )
        self.assertIn("pinned upstream blob", mismatch or "")

    def test_untracked_or_ignored_runtime_code_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir()
            (root / "scripts" / "inference.py").write_bytes(b"placeholder")
            with mock.patch(
                "uv_studio.capabilities.adapters.musetalk_verified._git_blob_sha1",
                return_value=MUSE_TALK_INFERENCE_BLOB_SHA1,
            ):
                source_shadow = _checkout_problem(
                    root,
                    runner=self._runner(
                        head=MUSE_TALK_UPSTREAM_COMMIT,
                        untracked="torch.py\0notes.txt\0",
                    ),
                    git_path="git",
                )
                ignored_bytecode = _checkout_problem(
                    root,
                    runner=self._runner(
                        head=MUSE_TALK_UPSTREAM_COMMIT,
                        ignored="musetalk/utils/__pycache__/utils.cpython-311.pyc\0",
                    ),
                    git_path="git",
                )
                ignored_local_tool = _checkout_problem(
                    root,
                    runner=self._runner(
                        head=MUSE_TALK_UPSTREAM_COMMIT,
                        ignored="ffmpeg\0",
                    ),
                    git_path="git",
                )
        self.assertIn("torch.py", source_shadow or "")
        self.assertIn(".pyc", ignored_bytecode or "")
        self.assertIn("ffmpeg", ignored_local_tool or "")

    def test_untracked_symlink_shadow_is_rejected_even_without_code_suffix(self) -> None:
        root = Path("checkout")
        with mock.patch.object(Path, "is_symlink", return_value=True):
            self.assertTrue(_runtime_path_is_untrusted(root, "torch"))
        with mock.patch.object(Path, "is_symlink", return_value=False):
            self.assertFalse(_runtime_path_is_untrusted(root, "notes"))

    def test_runtime_environment_and_non_code_data_are_not_treated_as_checkout_code(self) -> None:
        self.assertFalse(_runtime_code_path(".venv/lib/python3.11/site-packages/torch/__init__.py"))
        self.assertFalse(_runtime_code_path("venv/Scripts/python.exe"))
        self.assertFalse(_runtime_code_path("models/musetalkV15/unet.pth"))
        self.assertFalse(_runtime_code_path("notes.txt"))
        self.assertTrue(_runtime_code_path("musetalk/__init__.py"))
        self.assertTrue(_runtime_code_path("cv2.pyd"))
        self.assertTrue(_runtime_code_path("ffmpeg"))

    def test_pinned_model_payloads_fail_closed_on_hash_or_loader_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for relative in _PINNED_MODEL_SHA256:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(relative.encode("utf-8"))

            def trusted_hasher(path: Path) -> str:
                relative = path.relative_to(root).as_posix()
                return _PINNED_MODEL_SHA256[relative]

            self.assertIsNone(_model_payload_problem(root, hasher=trusted_hasher))

            mismatched_relative = "models/musetalkV15/unet.pth"

            def mismatched_hasher(path: Path) -> str:
                relative = path.relative_to(root).as_posix()
                if relative == mismatched_relative:
                    return "0" * 64
                return _PINNED_MODEL_SHA256[relative]

            mismatch = _model_payload_problem(root, hasher=mismatched_hasher)
            self.assertIn(mismatched_relative, mismatch or "")
            self.assertIn("hash mismatch", mismatch or "")

            alternative = root / "models/sd-vae/diffusion_pytorch_model.safetensors"
            alternative.write_bytes(b"different-loader-payload")
            override = _model_payload_problem(root, hasher=trusted_hasher)
            self.assertIn("alternative model payload", override or "")
            self.assertIn("safetensors", override or "")

    def test_runtime_probe_requires_importable_environment_and_cuda(self) -> None:
        python = Path("python")

        def completed(returncode: int):
            def run(command, **kwargs):
                self.assertEqual(command[0], str(python))
                self.assertEqual(command[1:3], ["-B", "-c"])
                return subprocess.CompletedProcess(command, returncode, "", "")
            return run

        self.assertIsNone(_runtime_problem(python, runner=completed(0)))
        self.assertIn("CUDA", _runtime_problem(python, runner=completed(3)) or "")
        self.assertIn("cannot import", _runtime_problem(python, runner=completed(1)) or "")

    def test_verified_adapter_disables_checkout_bytecode_writes_for_musetalk_invocation(self) -> None:
        adapter = object.__new__(MuseTalkAdapter)
        with mock.patch.object(
            MuseTalkAdapter.__mro__[1],
            "_invoke",
            return_value=subprocess.CompletedProcess([], 0, "", ""),
        ) as base_invoke:
            adapter._invoke(
                ["python", "-m", "scripts.inference", "--version", "v15"],
                cwd=Path("checkout"),
                tool="MuseTalk",
            )
        command = base_invoke.call_args.args[0]
        self.assertEqual(command[:4], ["python", "-B", "-m", "scripts.inference"])

    def test_hash_helpers_match_expected_formats(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "file.py"
            body = b"print('uv')\n"
            path.write_bytes(body)
            expected_blob = hashlib.sha1(
                f"blob {len(body)}\0".encode("ascii") + body,
                usedforsecurity=False,
            ).hexdigest()
            self.assertEqual(_git_blob_sha1(path), expected_blob)
            self.assertEqual(_sha256_file(path), hashlib.sha256(body).hexdigest())


if __name__ == "__main__":
    unittest.main()
