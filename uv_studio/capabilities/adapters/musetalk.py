"""Optional local MuseTalk 1.5 lip-sync adapter over project-owned portrait + speech."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import uuid
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from uv_studio.projects.models import ProjectReference
from uv_studio.projects.source_media import ProjectSourceMediaStore, SourceMediaError
from uv_studio.projects.store import ProjectStore

from ..execution import (
    CapabilityExecutionResult,
    CapabilityToolFailed,
    CapabilityToolUnavailable,
    InvalidCapabilityInput,
    UnsupportedCapabilityExecution,
)
from ..models import (
    AdapterDefinition,
    AdapterKind,
    CapabilityOffer,
    CostClass,
    LocalityClass,
    OfferAvailability,
)
from ..registry import CapabilityRegistry

MUSE_TALK_UPSTREAM_COMMIT = "0a89dec45a0192b824e3cf4daf96c239440c5ed8"
_ADAPTER_ID = "local_musetalk"
_OFFER_ID = "local_musetalk.video_digital_human"
_MAX_SPEECH_DURATION_US = 30 * 60 * 1_000_000
_DEFAULT_TIMEOUT_SEC = 2 * 60 * 60
_REQUIRED_RELATIVE_PATHS = (
    "scripts/inference.py",
    "models/musetalkV15/unet.pth",
    "models/musetalkV15/musetalk.json",
    "models/sd-vae/config.json",
    "models/sd-vae/diffusion_pytorch_model.bin",
    "models/whisper/config.json",
    "models/whisper/pytorch_model.bin",
    "models/whisper/preprocessor_config.json",
    "models/dwpose/dw-ll_ucoco_384.pth",
    "models/face-parse-bisent/79999_iter.pth",
    "models/face-parse-bisent/resnet18-5c106cde.pth",
)
RunCommand = Callable[..., subprocess.CompletedProcess[str]]


def _run_command(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
    return subprocess.run(*args, **kwargs)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _yaml_single(value: Path | str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _configured_root(value: str | Path | None = None) -> Path | None:
    raw = value if value is not None else os.environ.get("UV_STUDIO_MUSETALK_ROOT")
    if raw is None:
        return None
    try:
        resolved = Path(raw).expanduser().resolve(strict=True)
    except OSError:
        return None
    return resolved if resolved.is_dir() else None


def _configured_python(root: Path | None, value: str | Path | None = None) -> Path | None:
    raw = value if value is not None else os.environ.get("UV_STUDIO_MUSETALK_PYTHON")
    candidates: list[Path] = []
    if raw is not None:
        candidates.append(Path(raw).expanduser())
    if root is not None:
        candidates.extend(
            [
                root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python"),
                root / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python"),
            ]
        )
    for candidate in candidates:
        try:
            resolved = candidate.resolve(strict=True)
        except OSError:
            continue
        if resolved.is_file():
            return resolved
    return None


def _missing_runtime_parts(root: Path | None, python: Path | None) -> list[str]:
    if root is None:
        return ["UV_STUDIO_MUSETALK_ROOT"]
    missing: list[str] = []
    if python is None:
        missing.append("MuseTalk Python environment")
    for relative in _REQUIRED_RELATIVE_PATHS:
        if not (root / relative).is_file():
            missing.append(relative)
    if shutil.which("ffmpeg") is None:
        missing.append("ffmpeg")
    if shutil.which("ffprobe") is None:
        missing.append("ffprobe")
    return missing


def register_musetalk_adapter(registry: CapabilityRegistry) -> None:
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
    registry.register_offer(
        CapabilityOffer(
            offer_id=_OFFER_ID,
            capability_id="video.digital_human",
            adapter_id=_ADAPTER_ID,
            title="MuseTalk 1.5 portrait + speech lip-sync",
            availability=OfferAvailability.AVAILABLE if not missing else OfferAvailability.CONFIGURATION_REQUIRED,
            reason=(
                "MuseTalk 1.5 optional pack найден; UV Studio будет выполнять локальный fp16 lip-sync."
                if not missing
                else "Настройте optional MuseTalk 1.5 pack: " + ", ".join(missing[:6])
            ),
            locality=LocalityClass.LOCAL,
            cost_class=CostClass.FREE,
            asynchronous=False,
            features=(
                "video.lip_sync",
                "image.portrait",
                "audio.supplied",
                "runtime.optional",
                "musetalk.v15",
                f"upstream.{MUSE_TALK_UPSTREAM_COMMIT[:12]}",
            ),
        )
    )


class MuseTalkAdapter:
    adapter_id = _ADAPTER_ID

    def __init__(
        self,
        store: ProjectStore,
        *,
        runner: RunCommand = _run_command,
        root_path: str | Path | None = None,
        python_path: str | Path | None = None,
        ffmpeg_path: str | Path | None = None,
        ffprobe_path: str | Path | None = None,
        timeout_sec: int = _DEFAULT_TIMEOUT_SEC,
    ) -> None:
        self.store = store
        self.source_media = ProjectSourceMediaStore(store)
        self.runner = runner
        self.root_path = root_path
        self.python_path = python_path
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self.timeout_sec = timeout_sec

    @staticmethod
    def _validate_offer(offer: CapabilityOffer) -> None:
        if offer.adapter_id != _ADAPTER_ID or offer.capability_id != "video.digital_human":
            raise UnsupportedCapabilityExecution("MuseTalk adapter received an incompatible offer")
        if offer.offer_id != _OFFER_ID:
            raise UnsupportedCapabilityExecution("MuseTalk adapter requires the exact pinned offer")
        if offer.availability is not OfferAvailability.AVAILABLE:
            raise UnsupportedCapabilityExecution("MuseTalk offer is not currently available")
        if offer.locality is not LocalityClass.LOCAL or offer.cost_class is not CostClass.FREE:
            raise UnsupportedCapabilityExecution("MuseTalk adapter accepts only local/free offers")

    @staticmethod
    def _runtime_file(value: str | Path | None, label: str) -> Path:
        if value is None:
            raise CapabilityToolUnavailable(f"{label} is not configured")
        try:
            path = Path(value).expanduser().resolve(strict=True)
        except OSError as exc:
            raise CapabilityToolUnavailable(f"{label} could not be resolved") from exc
        if not path.is_file():
            raise CapabilityToolUnavailable(f"{label} is not a regular file")
        return path

    def _runtime(self) -> tuple[Path, Path, Path, Path]:
        root = _configured_root(self.root_path)
        python = _configured_python(root, self.python_path)
        missing = _missing_runtime_parts(root, python)
        if missing:
            raise CapabilityToolUnavailable("MuseTalk runtime is incomplete: " + ", ".join(missing[:8]))
        assert root is not None and python is not None
        ffmpeg = self._runtime_file(self.ffmpeg_path or shutil.which("ffmpeg"), "ffmpeg")
        ffprobe = self._runtime_file(self.ffprobe_path or shutil.which("ffprobe"), "ffprobe")
        return root, python, ffmpeg, ffprobe

    def _invoke(self, command: list[str], *, cwd: Path, tool: str) -> subprocess.CompletedProcess[str]:
        try:
            completed = self.runner(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=self.timeout_sec,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise CapabilityToolFailed(f"{tool} execution failed: {exc}") from exc
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "").strip()
            raise CapabilityToolFailed(
                f"{tool} exited with code {completed.returncode}" + (f": {detail[:800]}" if detail else "")
            )
        return completed

    def _probe(self, ffprobe: Path, path: Path, *, cwd: Path) -> tuple[int, int | None, int | None]:
        completed = self._invoke(
            [str(ffprobe), "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
            cwd=cwd,
            tool="ffprobe",
        )
        try:
            payload = json.loads(completed.stdout)
        except (TypeError, json.JSONDecodeError) as exc:
            raise CapabilityToolFailed("ffprobe returned malformed MuseTalk output metadata") from exc
        streams = payload.get("streams") if isinstance(payload, Mapping) else None
        if not isinstance(streams, list):
            raise CapabilityToolFailed("MuseTalk output probe is missing streams")
        video = next((item for item in streams if isinstance(item, Mapping) and item.get("codec_type") == "video"), None)
        audio = next((item for item in streams if isinstance(item, Mapping) and item.get("codec_type") == "audio"), None)
        if video is None or audio is None:
            raise CapabilityToolFailed("MuseTalk output must contain both video and audio")
        format_data = payload.get("format") if isinstance(payload, Mapping) else None
        raw_duration = format_data.get("duration") if isinstance(format_data, Mapping) else None
        try:
            duration_us = int(round(float(raw_duration) * 1_000_000))
        except (TypeError, ValueError) as exc:
            raise CapabilityToolFailed("MuseTalk output has no valid duration") from exc
        if duration_us <= 0:
            raise CapabilityToolFailed("MuseTalk output duration must be positive")
        width = video.get("width") if isinstance(video.get("width"), int) else None
        height = video.get("height") if isinstance(video.get("height"), int) else None
        return duration_us, width, height

    def execute(
        self,
        *,
        project_id: str,
        offer: CapabilityOffer,
        payload: Mapping[str, Any],
    ) -> CapabilityExecutionResult:
        self._validate_offer(offer)
        if not isinstance(payload, Mapping):
            raise InvalidCapabilityInput("video.digital_human input must be a JSON object")
        allowed = {"portrait_source_id", "speech_source_id"}
        unknown = set(payload).difference(allowed)
        if unknown:
            raise InvalidCapabilityInput(f"unsupported MuseTalk input fields: {sorted(unknown)!r}")
        portrait_id = payload.get("portrait_source_id")
        speech_id = payload.get("speech_source_id")
        if not isinstance(portrait_id, str) or not portrait_id.strip():
            raise InvalidCapabilityInput("portrait_source_id must be a non-empty string")
        if not isinstance(speech_id, str) or not speech_id.strip():
            raise InvalidCapabilityInput("speech_source_id must be a non-empty string")
        try:
            portrait, portrait_path = self.source_media.resolve_verified(project_id, portrait_id.strip(), expected_kind="image")
            speech, speech_path = self.source_media.resolve_verified(project_id, speech_id.strip(), expected_kind="audio")
        except SourceMediaError as exc:
            raise InvalidCapabilityInput(str(exc)) from exc
        duration_us = speech.metadata.get("duration_us")
        if isinstance(duration_us, bool) or not isinstance(duration_us, int) or duration_us <= 0:
            raise InvalidCapabilityInput("registered speech source has no trusted positive duration")
        if duration_us > _MAX_SPEECH_DURATION_US:
            raise InvalidCapabilityInput("MuseTalk execution is limited to 30 minutes per task")

        root, python, ffmpeg, ffprobe = self._runtime()
        artifact_id = f"art_{uuid.uuid4().hex}"
        canonical_output = f"artifacts/{artifact_id}.mp4"
        output_path = self.store.resolve_project_file(project_id, canonical_output, must_exist=False, allowed_roots=("artifacts",))
        tasks_dir = self.store.project_directory(project_id) / "tasks"
        try:
            with tempfile.TemporaryDirectory(prefix="musetalk-", dir=tasks_dir) as tmp:
                task_dir = Path(tmp)
                avatar_video = task_dir / "avatar.mp4"
                result_dir = task_dir / "results"
                config_path = task_dir / "inference.yaml"
                self._invoke(
                    [
                        str(ffmpeg), "-hide_banner", "-loglevel", "error", "-y",
                        "-loop", "1", "-i", str(portrait_path), "-t", f"{duration_us}us", "-r", "25",
                        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p",
                        "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18", str(avatar_video),
                    ],
                    cwd=task_dir,
                    tool="ffmpeg",
                )
                if not avatar_video.is_file() or avatar_video.stat().st_size <= 0:
                    raise CapabilityToolFailed("failed to prepare MuseTalk avatar video")
                config_path.write_text(
                    "task_0:\n"
                    f"  video_path: {_yaml_single(avatar_video)}\n"
                    f"  audio_path: {_yaml_single(speech_path)}\n"
                    "  result_name: 'output.mp4'\n",
                    encoding="utf-8",
                )
                self._invoke(
                    [
                        str(python), "-m", "scripts.inference",
                        "--inference_config", str(config_path),
                        "--result_dir", str(result_dir),
                        "--unet_model_path", str(root / "models/musetalkV15/unet.pth"),
                        "--unet_config", str(root / "models/musetalkV15/musetalk.json"),
                        "--whisper_dir", str(root / "models/whisper"),
                        "--version", "v15", "--fps", "25", "--use_float16",
                        "--ffmpeg_path", str(ffmpeg.parent),
                    ],
                    cwd=root,
                    tool="MuseTalk",
                )
                generated = result_dir / "v15" / "output.mp4"
                if not generated.is_file() or generated.is_symlink() or generated.stat().st_size <= 0:
                    raise CapabilityToolFailed("MuseTalk did not produce the expected output.mp4")
                actual_duration_us, width, height = self._probe(ffprobe, generated, cwd=task_dir)
                if abs(actual_duration_us - duration_us) > 1_000_000:
                    raise CapabilityToolFailed("MuseTalk output duration does not match supplied speech")
                shutil.copy2(generated, output_path)

            if not output_path.is_file() or output_path.is_symlink() or output_path.stat().st_size <= 0:
                raise CapabilityToolFailed("MuseTalk artifact copy failed")
            artifact = ProjectReference(
                id=artifact_id,
                kind="video",
                path=canonical_output,
                metadata={
                    "capability_id": offer.capability_id,
                    "offer_id": offer.offer_id,
                    "lifecycle": "performance_lip_sync_render",
                    "engine": "musetalk_v15",
                    "upstream_commit": MUSE_TALK_UPSTREAM_COMMIT,
                    "content_type": "video/mp4",
                    "portrait_binding": {
                        "source_id": portrait.id, "path": portrait.path,
                        "sha256": portrait.metadata.get("sha256"), "size_bytes": portrait.metadata.get("size_bytes"),
                    },
                    "speech_binding": {
                        "source_id": speech.id, "path": speech.path,
                        "sha256": speech.metadata.get("sha256"), "size_bytes": speech.metadata.get("size_bytes"),
                    },
                    "expected_duration_us": duration_us,
                    "actual_duration_us": actual_duration_us,
                    "width": width,
                    "height": height,
                    "sha256": _sha256_file(output_path),
                    "size_bytes": output_path.stat().st_size,
                },
            )
            project = self.store.load_project(project_id)
            self.store.update_project(project_id, artifacts=(*project.artifacts, artifact))
        except Exception:
            output_path.unlink(missing_ok=True)
            raise

        return CapabilityExecutionResult.from_offer(
            project_id=project_id,
            offer=offer,
            output={"path": canonical_output, "artifact_id": artifact_id, "duration_us": actual_duration_us, "engine": "musetalk_v15"},
            artifact=artifact.to_dict(),
        )
