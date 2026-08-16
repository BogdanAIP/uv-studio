"""Verified product wrapper for the optional MuseTalk 1.5 runtime.

The base adapter owns bounded execution. This wrapper makes the public offer
available only for the exact clean upstream checkout and executable CUDA
Python environment inspected by UV Studio.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path
from typing import Any

from ..execution import CapabilityToolUnavailable
from ..models import (
    AdapterDefinition,
    AdapterKind,
    CapabilityOffer,
    CostClass,
    LocalityClass,
    OfferAvailability,
)
from ..registry import CapabilityRegistry
from .musetalk import (
    MUSE_TALK_UPSTREAM_COMMIT,
    MuseTalkAdapter as BaseMuseTalkAdapter,
    _configured_python,
    _configured_root,
    _missing_runtime_parts,
)

MUSE_TALK_INFERENCE_BLOB_SHA1 = "428afb99a8fbb3175598e18c096b12dbfdf943d5"
_ADAPTER_ID = "local_musetalk"
_OFFER_ID = "local_musetalk.video_digital_human"
_RUNTIME_PROBE = (
    "import cv2, omegaconf, torch, transformers; "
    "raise SystemExit(0 if torch.cuda.is_available() else 3)"
)


def _git_blob_sha1(path: Path) -> str:
    body = path.read_bytes()
    digest = hashlib.sha1(usedforsecurity=False)
    digest.update(f"blob {len(body)}\0".encode("ascii"))
    digest.update(body)
    return digest.hexdigest()


def _checkout_problem(
    root: Path,
    *,
    runner: Any = subprocess.run,
    git_path: str | None = None,
) -> str | None:
    git = git_path or shutil.which("git")
    if not git:
        return "git is required to verify the pinned MuseTalk checkout"
    try:
        head = runner(
            [git, "-C", str(root), "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        status = runner(
            [git, "-C", str(root), "status", "--porcelain", "--untracked-files=no"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"MuseTalk git provenance check failed: {exc}"
    if head.returncode != 0:
        return "MuseTalk root is not a readable git checkout"
    if (head.stdout or "").strip().lower() != MUSE_TALK_UPSTREAM_COMMIT:
        return f"MuseTalk checkout must be pinned to {MUSE_TALK_UPSTREAM_COMMIT}"
    if status.returncode != 0:
        return "MuseTalk git worktree status could not be verified"
    if (status.stdout or "").strip():
        return "MuseTalk tracked worktree must be clean before execution"
    inference = root / "scripts" / "inference.py"
    try:
        fingerprint = _git_blob_sha1(inference)
    except OSError:
        return "MuseTalk scripts/inference.py could not be fingerprinted"
    if fingerprint != MUSE_TALK_INFERENCE_BLOB_SHA1:
        return "MuseTalk scripts/inference.py does not match the pinned upstream blob"
    return None


def _runtime_problem(
    python: Path,
    *,
    runner: Any = subprocess.run,
) -> str | None:
    try:
        completed = runner(
            [str(python), "-c", _RUNTIME_PROBE],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "MuseTalk Python runtime probe could not be executed"
    if completed.returncode == 3:
        return "MuseTalk fp16 offer requires an available CUDA device"
    if completed.returncode != 0:
        return "MuseTalk Python environment cannot import the required inference runtime"
    return None


def register_musetalk_adapter(registry: CapabilityRegistry) -> None:
    """Register only a truthfully executable exact MuseTalk checkout."""

    registry.register_adapter(
        AdapterDefinition(
            adapter_id=_ADAPTER_ID,
            title="MuseTalk 1.5 optional local lip-sync pack",
            description=(
                "Опциональный локальный MuseTalk 1.5 runtime для supplied portrait + speech. "
                "Модели/Python/CUDA не входят в обязательные зависимости UV Studio."
            ),
            kind=AdapterKind.LOCAL,
        )
    )
    root = _configured_root()
    python = _configured_python(root)
    missing = _missing_runtime_parts(root, python)
    verification_problem = None
    if not missing and root is not None and python is not None:
        verification_problem = _checkout_problem(root) or _runtime_problem(python)
    available = not missing and verification_problem is None
    if available:
        reason = (
            "MuseTalk 1.5 optional pack найден, проверен как чистый pinned checkout и "
            "подтвердил CUDA runtime; UV Studio будет выполнять локальный fp16 lip-sync."
        )
    elif missing:
        reason = "Настройте optional MuseTalk 1.5 pack: " + ", ".join(missing[:6])
    else:
        reason = verification_problem or "MuseTalk runtime could not be verified"
    registry.register_offer(
        CapabilityOffer(
            offer_id=_OFFER_ID,
            capability_id="video.digital_human",
            adapter_id=_ADAPTER_ID,
            title="MuseTalk 1.5 portrait + speech lip-sync",
            availability=(
                OfferAvailability.AVAILABLE
                if available
                else OfferAvailability.CONFIGURATION_REQUIRED
            ),
            reason=reason,
            locality=LocalityClass.LOCAL,
            cost_class=CostClass.FREE,
            asynchronous=False,
            features=(
                "video.lip_sync",
                "image.portrait",
                "audio.supplied",
                "runtime.optional",
                "runtime.cuda",
                "musetalk.v15",
                f"upstream.{MUSE_TALK_UPSTREAM_COMMIT[:12]}",
                f"inference_blob.{MUSE_TALK_INFERENCE_BLOB_SHA1[:12]}",
            ),
        )
    )


class MuseTalkAdapter(BaseMuseTalkAdapter):
    """Base bounded executor plus exact checkout/CUDA verification at execution time."""

    adapter_id = _ADAPTER_ID

    def _runtime(self):
        root, python, ffmpeg, ffprobe = super()._runtime()
        problem = _checkout_problem(root) or _runtime_problem(python)
        if problem is not None:
            raise CapabilityToolUnavailable(problem)
        return root, python, ffmpeg, ffprobe
