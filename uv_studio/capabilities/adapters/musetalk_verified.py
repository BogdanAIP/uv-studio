"""Verified product wrapper for the optional MuseTalk 1.5 runtime.

The base adapter owns bounded execution. This wrapper makes the public offer
available only for the exact reviewed upstream checkout, model payloads and
executable CUDA Python environment inspected by UV Studio.
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
_RUNTIME_PROFILE = "musetalk_v15_uv_verified_sha256_v1"
_RUNTIME_PROBE = (
    "import cv2, omegaconf, torch, transformers; "
    "raise SystemExit(0 if torch.cuda.is_available() else 3)"
)
_RUNTIME_ENV_PREFIXES = (".venv/", "venv/")
_IGNORED_DATA_PREFIXES = ("models/", "results/", "dataset/")
_UNTRUSTED_RUNTIME_SUFFIXES = frozenset(
    {
        ".py",
        ".pyw",
        ".pyc",
        ".pyo",
        ".pyd",
        ".so",
        ".dll",
        ".dylib",
        ".exe",
        ".com",
        ".bat",
        ".cmd",
        ".ps1",
        ".sh",
    }
)
_UNTRUSTED_RUNTIME_NAMES = frozenset({"ffmpeg", "ffprobe", "ffplay"})

# These are the exact binary payloads used by the MuseTalk 1.5 download layout
# accepted by UV Studio. Several are loaded through torch.load / legacy PyTorch
# serialization, so existence alone is not a sufficient execution boundary.
_PINNED_MODEL_SHA256 = {
    "models/musetalkV15/unet.pth": "7ebf6c98c181e20838e4c0054e96e944ac60d5d692cc01db42839fe11b787007",
    "models/sd-vae/diffusion_pytorch_model.bin": "1b4889b6b1d4ce7ae320a02dedaeff1780ad77d415ea0d744b476155c6377ddc",
    "models/whisper/pytorch_model.bin": "9607f98a2b22d9e229ae43c52ecea79dcede9e0c5cfae67e8da6eda86d8aac1d",
    "models/dwpose/dw-ll_ucoco_384.pth": "0d9408b13cd863c4e95a149dd31232f88f2a12aa6cf8964ed74d7d97748c7a07",
    "models/face-parse-bisent/79999_iter.pth": "468e13ca13a9b43cc0881a9f99083a430e9c0a38abd935431d1c28ee94b26567",
    "models/face-parse-bisent/resnet18-5c106cde.pth": "5c106cde386e87d4033832f2996f5493238eda96ccf559d1d62760c4de0613f8",
}

# The accepted Stage 8 layout deliberately follows MuseTalk's bounded download
# script, which selects the legacy .bin payloads below. If an alternative file
# is present, current Diffusers/Transformers resolution may prefer it instead of
# the pinned file, so the offer must fail closed rather than execute different
# model bytes than those verified above.
_ALTERNATIVE_MODEL_PAYLOADS = (
    "models/sd-vae/diffusion_pytorch_model.safetensors",
    "models/whisper/model.safetensors",
)


def _git_blob_sha1(path: Path) -> str:
    body = path.read_bytes()
    digest = hashlib.sha1(usedforsecurity=False)
    digest.update(f"blob {len(body)}\0".encode("ascii"))
    digest.update(body)
    return digest.hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_runtime_relative_path(relative: str) -> str:
    return relative.replace("\\", "/").lstrip("./")


def _runtime_code_path(relative: str) -> bool:
    normalized = _normalize_runtime_relative_path(relative)
    if not normalized or normalized.startswith(_RUNTIME_ENV_PREFIXES):
        return False
    name = normalized.rsplit("/", 1)[-1].lower()
    suffix = Path(name).suffix.lower()
    return suffix in _UNTRUSTED_RUNTIME_SUFFIXES or name in _UNTRUSTED_RUNTIME_NAMES


def _runtime_path_is_untrusted(root: Path, relative: str) -> bool:
    normalized = _normalize_runtime_relative_path(relative)
    if not normalized or normalized.startswith(_RUNTIME_ENV_PREFIXES):
        return False
    if _runtime_code_path(normalized):
        return True
    return (root / normalized).is_symlink()


def _untracked_runtime_problem(
    root: Path,
    git: str,
    *,
    runner: Any = subprocess.run,
) -> str | None:
    """Reject checkout-local code, binaries or symlinks that tracked-clean Git status cannot see.

    MuseTalk intentionally keeps model weights, generated results/datasets and often a
    local virtual environment outside Git. Those data/runtime-environment paths are
    valid, but checkout-local importable code, executables or symlink shadows can alter
    what Python or an external tool resolves when upstream inference runs from the repo.
    """

    exclude_env = (":(exclude).venv/**", ":(exclude)venv/**")
    exclude_ignored_data = tuple(
        f":(exclude){prefix}**" for prefix in _IGNORED_DATA_PREFIXES
    )
    try:
        untracked = runner(
            [
                git,
                "-C",
                str(root),
                "ls-files",
                "--others",
                "--exclude-standard",
                "-z",
                "--",
                *exclude_env,
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        ignored = runner(
            [
                git,
                "-C",
                str(root),
                "ls-files",
                "--others",
                "--ignored",
                "--exclude-standard",
                "-z",
                "--",
                *exclude_env,
                *exclude_ignored_data,
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"MuseTalk untracked runtime-code check failed: {exc}"
    if untracked.returncode != 0 or ignored.returncode != 0:
        return "MuseTalk untracked runtime-code state could not be verified"

    candidates = [
        item
        for output in (untracked.stdout or "", ignored.stdout or "")
        for item in output.split("\0")
        if item
    ]
    unsafe = sorted(
        {
            _normalize_runtime_relative_path(item)
            for item in candidates
            if _runtime_path_is_untrusted(root, item)
        }
    )
    if unsafe:
        preview = ", ".join(unsafe[:4])
        if len(unsafe) > 4:
            preview += f", +{len(unsafe) - 4} more"
        return (
            "MuseTalk checkout contains untracked executable/importable/symlink runtime files; "
            f"remove them before execution: {preview}"
        )
    return None


def _model_payload_problem(
    root: Path,
    *,
    hasher: Any = _sha256_file,
) -> str | None:
    """Verify every executable model payload before it can reach PyTorch loaders."""

    for relative in _ALTERNATIVE_MODEL_PAYLOADS:
        path = root / relative
        if path.exists() or path.is_symlink():
            return (
                "MuseTalk verified layout contains an alternative model payload that may "
                f"override pinned bytes: {relative}"
            )

    for relative, expected_sha256 in _PINNED_MODEL_SHA256.items():
        path = root / relative
        try:
            if not path.is_file() or path.is_symlink():
                return f"MuseTalk pinned model payload is not a regular file: {relative}"
            actual_sha256 = hasher(path)
        except OSError as exc:
            return f"MuseTalk pinned model payload could not be verified ({relative}): {exc}"
        if actual_sha256.lower() != expected_sha256:
            return f"MuseTalk pinned model payload hash mismatch: {relative}"
    return None


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
    untracked_problem = _untracked_runtime_problem(root, git, runner=runner)
    if untracked_problem is not None:
        return untracked_problem
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
            [str(python), "-B", "-c", _RUNTIME_PROBE],
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
    """Register only a truthfully executable exact MuseTalk checkout and model payload."""

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
        verification_problem = (
            _checkout_problem(root)
            or _model_payload_problem(root)
            or _runtime_problem(python)
        )
    available = not missing and verification_problem is None
    if available:
        reason = (
            "MuseTalk 1.5 optional pack найден, проверен как pinned checkout без "
            "неотслеживаемого исполняемого/импортируемого/symlink-кода, с точными "
            "модельными payload SHA-256 и доступным CUDA runtime; UV Studio будет "
            "выполнять локальный fp16 lip-sync."
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
                "runtime.model_sha256",
                "musetalk.v15",
                f"upstream.{MUSE_TALK_UPSTREAM_COMMIT[:12]}",
                f"inference_blob.{MUSE_TALK_INFERENCE_BLOB_SHA1[:12]}",
            ),
        )
    )


class MuseTalkAdapter(BaseMuseTalkAdapter):
    """Base bounded executor plus exact checkout/model/CUDA verification at execution time."""

    adapter_id = _ADAPTER_ID
    runtime_profile = _RUNTIME_PROFILE
    model_payload_sha256 = dict(_PINNED_MODEL_SHA256)

    def _invoke(
        self,
        command: list[str],
        *,
        cwd: Path,
        tool: str,
    ) -> subprocess.CompletedProcess[str]:
        verified_command = command
        if tool == "MuseTalk" and len(command) >= 2 and command[1] != "-B":
            verified_command = [command[0], "-B", *command[1:]]
        return super()._invoke(verified_command, cwd=cwd, tool=tool)

    def _runtime(self):
        root, python, ffmpeg, ffprobe = super()._runtime()
        problem = (
            _checkout_problem(root)
            or _model_payload_problem(root)
            or _runtime_problem(python)
        )
        if problem is not None:
            raise CapabilityToolUnavailable(problem)
        return root, python, ffmpeg, ffprobe
