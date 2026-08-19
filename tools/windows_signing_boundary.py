#!/usr/bin/env python3
"""Validate the UV-owned Windows Authenticode signing/publication boundary."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Sequence

_SCHEMA_VERSION = 1
_PLATFORM = "windows-x86_64"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_TARGET_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


class WindowsSigningBoundaryError(RuntimeError):
    pass


def _read_json(path: Path | str, label: str) -> dict[str, Any]:
    candidate = Path(path)
    if candidate.is_symlink() or not candidate.is_file():
        raise WindowsSigningBoundaryError(f"{label} must be a regular file")
    try:
        value = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise WindowsSigningBoundaryError(f"{label} is not valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise WindowsSigningBoundaryError(f"{label} root must be an object")
    return value


def _normalized_relative(raw: object, label: str) -> str:
    if not isinstance(raw, str) or not raw or "\\" in raw:
        raise WindowsSigningBoundaryError(f"{label} must be a non-empty '/' path")
    path = Path(raw)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise WindowsSigningBoundaryError(f"{label} is not normalized: {raw!r}")
    return path.as_posix()


def _basename(raw: object, label: str) -> str:
    if not isinstance(raw, str) or not raw or Path(raw).name != raw or "/" in raw or "\\" in raw:
        raise WindowsSigningBoundaryError(f"{label} must be a basename")
    return raw


def _regular_file(path: Path | str, label: str) -> Path:
    candidate = Path(path).expanduser()
    if candidate.is_symlink():
        raise WindowsSigningBoundaryError(f"{label} must not be a symlink")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise WindowsSigningBoundaryError(f"{label} is missing") from exc
    if not resolved.is_file():
        raise WindowsSigningBoundaryError(f"{label} must be a regular file")
    return resolved


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_json(path: Path | str, value: dict[str, Any]) -> Path:
    target = Path(path).expanduser()
    if target.is_symlink():
        raise WindowsSigningBoundaryError("evidence output must not be a symlink")
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
        os.replace(temp_name, target)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise
    return target.resolve()


def load_and_validate_policy(policy_file: Path | str) -> dict[str, Any]:
    raw = _read_json(policy_file, "Windows signing policy")
    if raw.get("schema_version") != _SCHEMA_VERSION:
        raise WindowsSigningBoundaryError(f"unsupported signing policy schema: {raw.get('schema_version')!r}")
    if raw.get("platform") != _PLATFORM:
        raise WindowsSigningBoundaryError(f"unexpected signing policy platform: {raw.get('platform')!r}")

    gate = raw.get("release_gate")
    if not isinstance(gate, dict):
        raise WindowsSigningBoundaryError("release_gate must be an object")
    prefixes = gate.get("forbidden_release_prefixes")
    if not isinstance(prefixes, list) or not prefixes:
        raise WindowsSigningBoundaryError("forbidden_release_prefixes must be non-empty")
    normalized_prefixes: list[str] = []
    for prefix in prefixes:
        relative = _normalized_relative(prefix.rstrip("/"), "forbidden release prefix") + "/"
        normalized_prefixes.append(relative.casefold())

    verification = raw.get("verification")
    if not isinstance(verification, dict):
        raise WindowsSigningBoundaryError("verification must be an object")
    for key in ("require_valid_authenticode", "expected_publisher_required", "require_trusted_timestamp"):
        if verification.get(key) is not True:
            raise WindowsSigningBoundaryError(f"verification.{key} must be true")

    publication = raw.get("publication")
    if not isinstance(publication, dict) or publication.get("checksums_after_all_signatures") is not True:
        raise WindowsSigningBoundaryError("publication must require checksums after all signatures")
    _basename(publication.get("checksum_manifest"), "checksum manifest")

    targets = raw.get("targets")
    if not isinstance(targets, list) or not targets:
        raise WindowsSigningBoundaryError("targets must be a non-empty list")
    ids: set[str] = set()
    release_paths: set[str] = set()
    kinds: set[str] = set()
    for target in targets:
        if not isinstance(target, dict):
            raise WindowsSigningBoundaryError("every signing target must be an object")
        target_id = target.get("id")
        if not isinstance(target_id, str) or _TARGET_ID_RE.fullmatch(target_id) is None or target_id in ids:
            raise WindowsSigningBoundaryError(f"invalid or duplicate signing target id: {target_id!r}")
        ids.add(target_id)
        kind = target.get("kind")
        if kind not in {"release_file", "artifact", "generated_executable"}:
            raise WindowsSigningBoundaryError(f"{target_id}: unsupported target kind")
        kinds.add(kind)
        if not isinstance(target.get("phase"), str) or not target["phase"]:
            raise WindowsSigningBoundaryError(f"{target_id}: phase must be non-empty")
        if target.get("required_for_public_release") is not True:
            raise WindowsSigningBoundaryError(f"{target_id}: public-release target must be required")
        if kind == "release_file":
            relative = _normalized_relative(target.get("path"), f"{target_id}: path")
            folded = relative.casefold()
            if any(folded.startswith(prefix) for prefix in normalized_prefixes):
                raise WindowsSigningBoundaryError(f"{target_id}: target is inside forbidden third-party/runtime prefix")
            if folded in release_paths:
                raise WindowsSigningBoundaryError(f"duplicate signing release path: {relative}")
            release_paths.add(folded)
        elif kind == "artifact":
            _basename(target.get("basename"), f"{target_id}: basename")

    if ids != {"backend", "desktop", "installer", "uninstaller"}:
        raise WindowsSigningBoundaryError(
            "public signing policy must contain exactly backend, desktop, installer and uninstaller"
        )
    if kinds != {"release_file", "artifact", "generated_executable"}:
        raise WindowsSigningBoundaryError("public signing policy target kinds are incomplete")
    return raw


def _target(policy: dict[str, Any], target_id: str) -> dict[str, Any]:
    for target in policy["targets"]:
        if target["id"] == target_id:
            return target
    raise WindowsSigningBoundaryError(f"unknown signing target: {target_id}")


def resolve_target_file(
    policy: dict[str, Any], target_id: str, file_path: Path | str, *, release_root: Path | str | None = None
) -> Path:
    target = _target(policy, target_id)
    candidate = _regular_file(file_path, f"{target_id} signing target")
    kind = target["kind"]
    if kind == "release_file":
        if release_root is None:
            raise WindowsSigningBoundaryError(f"{target_id}: release_root is required")
        root = Path(release_root).expanduser()
        if root.is_symlink() or not root.is_dir():
            raise WindowsSigningBoundaryError("release_root must be a real directory")
        root = root.resolve(strict=True)
        expected = root.joinpath(*target["path"].split("/")).resolve(strict=False)
        if candidate != expected:
            raise WindowsSigningBoundaryError(
                f"{target_id}: signing target must be exact policy path {target['path']}"
            )
    elif kind == "artifact":
        if candidate.name.casefold() != target["basename"].casefold():
            raise WindowsSigningBoundaryError(f"{target_id}: artifact basename does not match policy")
    else:
        if candidate.suffix.casefold() != ".exe":
            raise WindowsSigningBoundaryError(f"{target_id}: generated signing target must be .exe")
    return candidate


def snapshot_unsigned_target(
    *, policy_file: Path | str, target_id: str, file_path: Path | str,
    output_file: Path | str, release_root: Path | str | None = None,
) -> dict[str, Any]:
    policy = load_and_validate_policy(policy_file)
    target = resolve_target_file(policy, target_id, file_path, release_root=release_root)
    evidence = {
        "schema_version": 1,
        "target_id": target_id,
        "target_kind": _target(policy, target_id)["kind"],
        "phase": _target(policy, target_id)["phase"],
        "bytes_before_signing": target.stat().st_size,
        "sha256_before_signing": _sha256(target),
    }
    _atomic_json(output_file, evidence)
    return evidence


def _powershell_executable() -> str:
    for name in ("pwsh.exe", "powershell.exe", "pwsh", "powershell"):
        executable = shutil.which(name)
        if executable:
            return executable
    raise WindowsSigningBoundaryError("PowerShell is required for Authenticode verification")


def _read_authenticode(path: Path) -> dict[str, Any]:
    if os.name != "nt":
        raise WindowsSigningBoundaryError("Authenticode verification requires Windows")
    script = r'''$ErrorActionPreference='Stop'; $s=Get-AuthenticodeSignature -LiteralPath $args[0]; [ordered]@{status=[string]$s.Status; status_message=[string]$s.StatusMessage; signer_subject=if($s.SignerCertificate){[string]$s.SignerCertificate.Subject}else{$null}; signer_thumbprint=if($s.SignerCertificate){[string]$s.SignerCertificate.Thumbprint}else{$null}; timestamp_subject=if($s.TimeStamperCertificate){[string]$s.TimeStamperCertificate.Subject}else{$null}; timestamp_thumbprint=if($s.TimeStamperCertificate){[string]$s.TimeStamperCertificate.Thumbprint}else{$null}} | ConvertTo-Json -Compress'''
    result = subprocess.run(
        [_powershell_executable(), "-NoProfile", "-NonInteractive", "-Command", script, str(path)],
        check=False, capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        raise WindowsSigningBoundaryError("PowerShell Authenticode inspection failed")
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise WindowsSigningBoundaryError("PowerShell Authenticode output was not JSON") from exc
    if not isinstance(value, dict):
        raise WindowsSigningBoundaryError("PowerShell Authenticode output was invalid")
    return value


def verify_signed_target(
    *, policy_file: Path | str, target_id: str, file_path: Path | str,
    expected_subject: str, output_file: Path | str,
    expected_thumbprint: str | None = None, before_file: Path | str | None = None,
    release_root: Path | str | None = None,
) -> dict[str, Any]:
    policy = load_and_validate_policy(policy_file)
    target = resolve_target_file(policy, target_id, file_path, release_root=release_root)
    if not isinstance(expected_subject, str) or not expected_subject.strip():
        raise WindowsSigningBoundaryError("expected publisher subject must be non-empty")
    if expected_thumbprint is not None:
        expected_thumbprint = expected_thumbprint.replace(" ", "").upper()
        if not expected_thumbprint or any(ch not in "0123456789ABCDEF" for ch in expected_thumbprint):
            raise WindowsSigningBoundaryError("expected publisher thumbprint is invalid")

    before: dict[str, Any] | None = None
    if before_file is not None:
        before = _read_json(before_file, "pre-sign snapshot")
        if before.get("target_id") != target_id:
            raise WindowsSigningBoundaryError("pre-sign snapshot target does not match")
        digest = before.get("sha256_before_signing")
        if not isinstance(digest, str) or _SHA256_RE.fullmatch(digest) is None:
            raise WindowsSigningBoundaryError("pre-sign snapshot SHA-256 is invalid")
        if digest == _sha256(target):
            raise WindowsSigningBoundaryError("signing did not change target bytes")

    signature = _read_authenticode(target)
    if str(signature.get("status", "")).casefold() != "valid":
        raise WindowsSigningBoundaryError(f"Authenticode status is not Valid: {signature.get('status')!r}")
    actual_subject = signature.get("signer_subject")
    if not isinstance(actual_subject, str) or actual_subject.casefold() != expected_subject.strip().casefold():
        raise WindowsSigningBoundaryError("Authenticode publisher subject does not match expected identity")
    actual_thumbprint = signature.get("signer_thumbprint")
    if expected_thumbprint is not None:
        normalized_actual = str(actual_thumbprint or "").replace(" ", "").upper()
        if normalized_actual != expected_thumbprint:
            raise WindowsSigningBoundaryError("Authenticode publisher thumbprint does not match")
    timestamp_subject = signature.get("timestamp_subject")
    timestamp_thumbprint = signature.get("timestamp_thumbprint")
    if not timestamp_subject or not timestamp_thumbprint:
        raise WindowsSigningBoundaryError("trusted timestamp certificate is missing")

    evidence = {
        "schema_version": 1,
        "target_id": target_id,
        "target_kind": _target(policy, target_id)["kind"],
        "phase": _target(policy, target_id)["phase"],
        "bytes_after_signing": target.stat().st_size,
        "sha256_after_signing": _sha256(target),
        "authenticode_status": "Valid",
        "publisher_subject": actual_subject,
        "publisher_thumbprint": actual_thumbprint,
        "timestamp_subject": timestamp_subject,
        "timestamp_thumbprint": timestamp_thumbprint,
        "pre_sign_sha256": None if before is None else before["sha256_before_signing"],
    }
    _atomic_json(output_file, evidence)
    return evidence


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate-policy")
    validate.add_argument("--policy", type=Path, required=True)

    snapshot = sub.add_parser("snapshot")
    snapshot.add_argument("--policy", type=Path, required=True)
    snapshot.add_argument("--target", required=True)
    snapshot.add_argument("--file", type=Path, required=True)
    snapshot.add_argument("--release-root", type=Path)
    snapshot.add_argument("--output", type=Path, required=True)

    verify = sub.add_parser("verify")
    verify.add_argument("--policy", type=Path, required=True)
    verify.add_argument("--target", required=True)
    verify.add_argument("--file", type=Path, required=True)
    verify.add_argument("--release-root", type=Path)
    verify.add_argument("--before", type=Path)
    verify.add_argument("--expected-subject", required=True)
    verify.add_argument("--expected-thumbprint")
    verify.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "validate-policy":
            policy = load_and_validate_policy(args.policy)
            print(json.dumps({"ok": True, "targets": [item["id"] for item in policy["targets"]]}, sort_keys=True))
        elif args.command == "snapshot":
            print(json.dumps(snapshot_unsigned_target(
                policy_file=args.policy, target_id=args.target, file_path=args.file,
                release_root=args.release_root, output_file=args.output,
            ), sort_keys=True))
        else:
            print(json.dumps(verify_signed_target(
                policy_file=args.policy, target_id=args.target, file_path=args.file,
                release_root=args.release_root, before_file=args.before,
                expected_subject=args.expected_subject, expected_thumbprint=args.expected_thumbprint,
                output_file=args.output,
            ), sort_keys=True))
    except (OSError, UnicodeError, WindowsSigningBoundaryError, subprocess.SubprocessError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
