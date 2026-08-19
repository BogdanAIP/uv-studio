from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.windows_signing_boundary import (
    WindowsSigningBoundaryError,
    load_and_validate_policy,
    resolve_target_file,
    snapshot_unsigned_target,
    verify_signed_target,
)


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "packaging" / "windows-signing-policy.windows-x86_64.json"
NSI = ROOT / "packaging" / "windows" / "uv-studio.nsi"


def _authenticode(
    *,
    status: str = "Valid",
    subject: str = "CN=UV Studio Test Publisher",
    thumbprint: str = "A1B2C3",
    timestamp_subject: str | None = "CN=Test Timestamp Authority",
    timestamp_thumbprint: str | None = "D4E5F6",
) -> dict[str, object]:
    return {
        "status": status,
        "status_message": "",
        "signer_subject": subject,
        "signer_thumbprint": thumbprint,
        "timestamp_subject": timestamp_subject,
        "timestamp_thumbprint": timestamp_thumbprint,
    }


class WindowsSigningBoundaryTests(unittest.TestCase):
    def test_production_policy_has_exact_uv_owned_targets(self) -> None:
        policy = load_and_validate_policy(POLICY)
        targets = {item["id"]: item for item in policy["targets"]}
        self.assertEqual(set(targets), {"backend", "desktop", "installer", "uninstaller"})
        self.assertEqual(targets["backend"]["path"], "backend/uv-studio-backend.exe")
        self.assertEqual(targets["desktop"]["path"], "desktop/uv-studio-desktop.exe")
        self.assertEqual(targets["desktop"]["phase"], "before-d044-manifest")
        self.assertEqual(
            targets["installer"]["basename"],
            "uv-studio-windows-x86_64-setup.exe",
        )
        self.assertEqual(targets["uninstaller"]["phase"], "nsis-uninstfinalize")
        self.assertEqual(
            set(policy["release_gate"]["forbidden_release_prefixes"]),
            {"runtime/", "frontend/", "backend/_internal/"},
        )
        self.assertTrue(policy["publication"]["checksums_after_all_signatures"])
        self.assertEqual(policy["publication"]["checksum_manifest"], "SHA256SUMS")

    def test_release_target_cannot_be_redirected_into_third_party_runtime(self) -> None:
        policy = load_and_validate_policy(POLICY)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "release"
            backend = root / "backend" / "uv-studio-backend.exe"
            ffmpeg = root / "runtime" / "media" / "Shotcut" / "ffmpeg.exe"
            backend.parent.mkdir(parents=True)
            ffmpeg.parent.mkdir(parents=True)
            backend.write_bytes(b"backend")
            ffmpeg.write_bytes(b"ffmpeg")
            self.assertEqual(
                resolve_target_file(policy, "backend", backend, release_root=root),
                backend.resolve(),
            )
            with self.assertRaises(WindowsSigningBoundaryError):
                resolve_target_file(policy, "backend", ffmpeg, release_root=root)

    def test_desktop_target_is_bounded_to_uv_owned_release_path(self) -> None:
        policy = load_and_validate_policy(POLICY)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "release"
            desktop = root / "desktop" / "uv-studio-desktop.exe"
            shadow = root / "runtime" / "uv-studio-desktop.exe"
            desktop.parent.mkdir(parents=True)
            shadow.parent.mkdir(parents=True)
            desktop.write_bytes(b"desktop")
            shadow.write_bytes(b"shadow")
            self.assertEqual(
                resolve_target_file(policy, "desktop", desktop, release_root=root),
                desktop.resolve(),
            )
            with self.assertRaises(WindowsSigningBoundaryError):
                resolve_target_file(policy, "desktop", shadow, release_root=root)

    def test_snapshot_and_signed_verification_bind_pre_and_post_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            release = root / "release"
            backend = release / "backend" / "uv-studio-backend.exe"
            backend.parent.mkdir(parents=True)
            backend.write_bytes(b"unsigned backend")
            before_file = root / "before.json"
            before = snapshot_unsigned_target(
                policy_file=POLICY,
                target_id="backend",
                file_path=backend,
                release_root=release,
                output_file=before_file,
            )
            self.assertEqual(before["sha256_before_signing"], hashlib.sha256(b"unsigned backend").hexdigest())

            backend.write_bytes(b"signed backend with authenticode bytes")
            output = root / "signed.json"
            with patch(
                "tools.windows_signing_boundary._read_authenticode",
                return_value=_authenticode(),
            ):
                evidence = verify_signed_target(
                    policy_file=POLICY,
                    target_id="backend",
                    file_path=backend,
                    release_root=release,
                    before_file=before_file,
                    expected_subject="CN=UV Studio Test Publisher",
                    expected_thumbprint="A1 B2 C3",
                    output_file=output,
                )
            self.assertEqual(evidence["authenticode_status"], "Valid")
            self.assertNotEqual(evidence["sha256_after_signing"], before["sha256_before_signing"])
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["target_id"], "backend")

    def test_unchanged_invalid_identity_or_missing_timestamp_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            installer = root / "uv-studio-windows-x86_64-setup.exe"
            installer.write_bytes(b"unsigned")
            before = root / "before.json"
            snapshot_unsigned_target(
                policy_file=POLICY,
                target_id="installer",
                file_path=installer,
                output_file=before,
            )

            with patch(
                "tools.windows_signing_boundary._read_authenticode",
                return_value=_authenticode(),
            ):
                with self.assertRaises(WindowsSigningBoundaryError):
                    verify_signed_target(
                        policy_file=POLICY,
                        target_id="installer",
                        file_path=installer,
                        before_file=before,
                        expected_subject="CN=UV Studio Test Publisher",
                        output_file=root / "unchanged.json",
                    )

            installer.write_bytes(b"changed")
            cases = (
                _authenticode(status="NotSigned"),
                _authenticode(subject="CN=Wrong Publisher"),
                _authenticode(timestamp_subject=None, timestamp_thumbprint=None),
            )
            for index, signature in enumerate(cases):
                with self.subTest(index=index), patch(
                    "tools.windows_signing_boundary._read_authenticode",
                    return_value=signature,
                ):
                    with self.assertRaises(WindowsSigningBoundaryError):
                        verify_signed_target(
                            policy_file=POLICY,
                            target_id="installer",
                            file_path=installer,
                            before_file=before,
                            expected_subject="CN=UV Studio Test Publisher",
                            output_file=root / f"bad-{index}.json",
                        )

    def test_generated_uninstaller_verification_is_extension_bounded(self) -> None:
        policy = load_and_validate_policy(POLICY)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            executable = root / "temporary-uninstaller.exe"
            text = root / "temporary-uninstaller.txt"
            executable.write_bytes(b"exe")
            text.write_bytes(b"text")
            self.assertEqual(
                resolve_target_file(policy, "uninstaller", executable),
                executable.resolve(),
            )
            with self.assertRaises(WindowsSigningBoundaryError):
                resolve_target_file(policy, "uninstaller", text)

    def test_nsis_script_has_guarded_installer_and_uninstaller_signing_hooks(self) -> None:
        text = NSI.read_text(encoding="utf-8")
        self.assertIn("!ifdef UV_SIGN_INSTALLER_COMMAND", text)
        self.assertIn("!finalize '${UV_SIGN_INSTALLER_COMMAND} \"%1\"' = 0", text)
        self.assertIn("!ifdef UV_SIGN_UNINSTALLER_COMMAND", text)
        self.assertIn("!uninstfinalize '${UV_SIGN_UNINSTALLER_COMMAND} \"%1\"' = 0", text)
        self.assertLess(text.index("!finalize"), text.index('InstallDir "$LOCALAPPDATA'))


if __name__ == "__main__":
    unittest.main()
