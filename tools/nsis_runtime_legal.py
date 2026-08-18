#!/usr/bin/env python3
"""Probe and stage exact NSIS source/license evidence for Stage 9."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import tarfile
import tempfile
import urllib.request
from pathlib import Path, PurePosixPath
from typing import Sequence
from urllib.parse import urlparse

_MAX_ARCHIVE_BYTES = 16 * 1024 * 1024
_MAX_MEMBER_COUNT = 20000
_MAX_EXPANDED_BYTES = 128 * 1024 * 1024
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class NSISLegalError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _https_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password or parsed.fragment:
        raise NSISLegalError("NSIS source URL must be credential-free HTTPS")
    return value


def _expected_sha(value: str | None) -> str | None:
    if value is None:
        return None
    if _SHA256_RE.fullmatch(value) is None:
        raise NSISLegalError("expected NSIS source SHA-256 must be 64 lowercase hex characters")
    return value


def _download(url: str, target: Path) -> tuple[int, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "uv-studio-stage9-nsis-legal/1"})
    total = 0
    digest = hashlib.sha256()
    try:
        with urllib.request.urlopen(request, timeout=60) as response, target.open("wb") as handle:
            final_url = response.geturl()
            if urlparse(final_url).scheme != "https":
                raise NSISLegalError("NSIS source download redirected away from HTTPS")
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > _MAX_ARCHIVE_BYTES:
                    raise NSISLegalError("NSIS source archive exceeded size limit")
                digest.update(chunk)
                handle.write(chunk)
    except NSISLegalError:
        raise
    except Exception as exc:
        raise NSISLegalError(f"NSIS source download failed: {exc}") from exc
    if total <= 0:
        raise NSISLegalError("NSIS source archive is empty")
    return total, digest.hexdigest()


def _canonical_member(name: str) -> PurePosixPath:
    if "\\" in name or not name or name.startswith("/"):
        raise NSISLegalError(f"unsafe NSIS source member path: {name!r}")
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise NSISLegalError(f"unsafe NSIS source member path: {name!r}")
    if path.as_posix() != name.rstrip("/"):
        raise NSISLegalError(f"non-canonical NSIS source member path: {name!r}")
    return path


def _read_copying(archive: Path, version: str) -> bytes:
    expected = f"nsis-{version}-src/COPYING"
    found: bytes | None = None
    member_count = 0
    expanded = 0
    try:
        with tarfile.open(archive, mode="r:bz2") as bundle:
            for member in bundle:
                member_count += 1
                if member_count > _MAX_MEMBER_COUNT:
                    raise NSISLegalError("NSIS source archive exceeded member-count limit")
                path = _canonical_member(member.name)
                if member.issym() or member.islnk() or member.isdev() or member.isfifo():
                    raise NSISLegalError(f"NSIS source archive contains unsupported member: {path}")
                if member.isfile():
                    if member.size < 0:
                        raise NSISLegalError(f"NSIS source archive has invalid member size: {path}")
                    expanded += member.size
                    if expanded > _MAX_EXPANDED_BYTES:
                        raise NSISLegalError("NSIS source archive exceeded expanded-size limit")
                    if path.as_posix() == expected:
                        if found is not None:
                            raise NSISLegalError("NSIS source archive contains duplicate COPYING")
                        handle = bundle.extractfile(member)
                        if handle is None:
                            raise NSISLegalError("NSIS source COPYING could not be read")
                        found = handle.read()
                elif not member.isdir():
                    raise NSISLegalError(f"NSIS source archive contains unsupported member type: {path}")
    except NSISLegalError:
        raise
    except (tarfile.TarError, OSError) as exc:
        raise NSISLegalError("NSIS source archive is not a readable tar.bz2") from exc
    if found is None:
        raise NSISLegalError(f"NSIS source archive is missing exact {expected}")
    if not found or len(found) > 2 * 1024 * 1024:
        raise NSISLegalError("NSIS source COPYING has invalid size")
    return found


def _atomic_json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def stage_nsis_legal(
    *,
    output_root: Path | str,
    version: str,
    source_url: str,
    expected_sha256: str | None = None,
) -> dict[str, object]:
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)+", version):
        raise NSISLegalError("NSIS version must be a canonical numeric version")
    url = _https_url(source_url)
    expected = _expected_sha(expected_sha256)
    output = Path(output_root)
    legal_root = output / "legal" / "nsis"
    if legal_root.exists() or legal_root.is_symlink():
        raise NSISLegalError("NSIS legal output already exists")

    temp_dir = Path(tempfile.mkdtemp(prefix="uv-nsis-source-"))
    archive = temp_dir / f"nsis-{version}-src.tar.bz2"
    try:
        archive_bytes, actual_sha = _download(url, archive)
        if expected is not None and actual_sha != expected:
            raise NSISLegalError(
                f"NSIS source SHA-256 mismatch: expected {expected}, got {actual_sha}"
            )
        copying = _read_copying(archive, version)
        legal_root.mkdir(parents=True)
        copying_path = legal_root / "COPYING.txt"
        copying_path.write_bytes(copying)
        evidence = {
            "schema_version": 1,
            "component": "nsis-generated-installer-stub",
            "version": version,
            "source_url": url,
            "source_archive_bytes": archive_bytes,
            "source_archive_sha256": actual_sha,
            "expected_sha256_enforced": expected is not None,
            "copying_path": "legal/nsis/COPYING.txt",
            "copying_bytes": len(copying),
            "copying_sha256": _sha256(copying_path),
        }
        _atomic_json(legal_root / "source-evidence.json", evidence)
    except Exception:
        shutil.rmtree(legal_root, ignore_errors=True)
        raise
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    return {"ok": True, **evidence}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--expected-sha256")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = stage_nsis_legal(
            output_root=args.output_root,
            version=args.version,
            source_url=args.source_url,
            expected_sha256=args.expected_sha256,
        )
    except (OSError, NSISLegalError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
