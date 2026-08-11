"""Bounded local FFmpeg/FFprobe capability execution.

No raw FFmpeg flags are accepted from API callers. All paths are resolved through
the canonical Project Store and subprocesses are invoked with argv + shell=False.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import uuid
from collections.abc import Callable, Mapping
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from uv_studio.projects.media_ranges import MICROSECONDS_PER_SECOND, ProjectMediaRange
from uv_studio.projects.models import ProjectReference, ProjectValidationError, validate_project_relative_path
from uv_studio.projects.store import ProjectStore, ProjectStoreError

from ..execution import (
    CapabilityExecutionResult,
    CapabilityToolFailed,
    CapabilityToolUnavailable,
    InvalidCapabilityInput,
    UnsupportedCapabilityExecution,
)
from ..models import CapabilityOffer, CostClass, LocalityClass, OfferAvailability

RunCommand = Callable[..., subprocess.CompletedProcess[str]]

_INPUT_ROOTS = ("sources", "assets", "artifacts", "exports")
_OUTPUT_ROOTS = ("artifacts", "exports")
_RANGE_OUTPUT_ROOTS = ("artifacts",)
_MAX_CONCAT_INPUTS = 200
_RANGE_EXTRACTION_MODE = "accurate_seek_lossless_ffv1_flac"


def _run_command(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
    return subprocess.run(*args, **kwargs)


def _parse_optional_float(value: Any) -> float | None:
    if value in (None, "", "N/A"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_duration_us(value: Any) -> int | None:
    if value in (None, "", "N/A"):
        return None
    try:
        duration = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    if not duration.is_finite() or duration < 0:
        return None
    return int(duration * MICROSECONDS_PER_SECOND)


def _canonical_project_path(value: str) -> str:
    try:
        return validate_project_relative_path(value)
    except ProjectValidationError as exc:
        raise InvalidCapabilityInput(str(exc)) from exc


def _ffconcat_quote(path: Path) -> str:
    # FFmpeg concat files understand forward-slash absolute paths on Windows too.
    # Single quotes are escaped using the concat demuxer's shell-like quoting form.
    value = path.resolve().as_posix().replace("'", "'\\''")
    return f"file '{value}'\n"


class LocalFFmpegAdapter:
    adapter_id = "local_ffmpeg"

    def __init__(
        self,
        store: ProjectStore,
        *,
        runner: RunCommand = _run_command,
        tool_paths: Mapping[str, str] | None = None,
        probe_timeout_sec: int = 60,
        assemble_timeout_sec: int = 600,
        extract_timeout_sec: int = 600,
    ) -> None:
        self.store = store
        self.runner = runner
        self.tool_paths = dict(tool_paths or {})
        self.probe_timeout_sec = probe_timeout_sec
        self.assemble_timeout_sec = assemble_timeout_sec
        self.extract_timeout_sec = extract_timeout_sec

    def _tool(self, name: str) -> str:
        configured = self.tool_paths.get(name)
        path = configured or shutil.which(name)
        if not path:
            raise CapabilityToolUnavailable(f"{name} is not available in this installation")
        return path

    @staticmethod
    def _validate_offer(offer: CapabilityOffer) -> None:
        if offer.adapter_id != LocalFFmpegAdapter.adapter_id:
            raise UnsupportedCapabilityExecution(
                f"local FFmpeg executor cannot run adapter {offer.adapter_id!r}"
            )
        if offer.availability is not OfferAvailability.AVAILABLE:
            raise UnsupportedCapabilityExecution(
                f"offer {offer.offer_id!r} is not currently available"
            )
        if offer.cost_class is not CostClass.FREE or offer.locality is not LocalityClass.LOCAL:
            raise UnsupportedCapabilityExecution(
                "local FFmpeg executor accepts only explicit free/local offers"
            )

    def execute(
        self,
        *,
        project_id: str,
        offer: CapabilityOffer,
        payload: Mapping[str, Any],
    ) -> CapabilityExecutionResult:
        self._validate_offer(offer)
        if not isinstance(payload, Mapping):
            raise InvalidCapabilityInput("capability input must be a JSON object")
        if offer.capability_id == "media.probe":
            return self._probe(project_id=project_id, offer=offer, payload=payload)
        if offer.capability_id == "video.extract_range":
            return self._extract_range(project_id=project_id, offer=offer, payload=payload)
        if offer.capability_id == "timeline.assemble":
            return self._assemble(project_id=project_id, offer=offer, payload=payload)
        raise UnsupportedCapabilityExecution(
            f"local FFmpeg executor does not implement {offer.capability_id!r}"
        )

    def _resolve_input_file(self, project_id: str, raw_path: str, *, operation: str) -> tuple[str, Path]:
        canonical_path = _canonical_project_path(raw_path)
        try:
            source = self.store.resolve_project_file(
                project_id,
                canonical_path,
                must_exist=True,
                allowed_roots=_INPUT_ROOTS,
            )
        except (ProjectValidationError, ProjectStoreError) as exc:
            raise InvalidCapabilityInput(str(exc)) from exc
        if not source.is_file():
            raise InvalidCapabilityInput(f"{operation} input is not a file: {canonical_path!r}")
        return canonical_path, source

    def _probe_path(self, *, canonical_path: str, source: Path) -> dict[str, Any]:
        command = [
            self._tool("ffprobe"),
            "-v",
            "error",
            "-show_format",
            "-show_streams",
            "-of",
            "json",
            str(source),
        ]
        completed = self._invoke(command, timeout=self.probe_timeout_sec, tool="ffprobe")
        try:
            data = json.loads(completed.stdout or "{}")
        except json.JSONDecodeError as exc:
            raise CapabilityToolFailed("ffprobe returned malformed JSON") from exc

        streams = data.get("streams") if isinstance(data, dict) else None
        if not isinstance(streams, list):
            streams = []
        format_data = data.get("format") if isinstance(data, dict) else None
        if not isinstance(format_data, dict):
            format_data = {}

        video_streams = [item for item in streams if isinstance(item, dict) and item.get("codec_type") == "video"]
        audio_streams = [item for item in streams if isinstance(item, dict) and item.get("codec_type") == "audio"]
        primary_video = video_streams[0] if video_streams else {}
        return {
            "path": canonical_path,
            "duration_sec": _parse_optional_float(format_data.get("duration")),
            "duration_us": _parse_duration_us(format_data.get("duration")),
            "format_name": format_data.get("format_name"),
            "size_bytes": int(format_data["size"]) if str(format_data.get("size", "")).isdigit() else None,
            "has_video": bool(video_streams),
            "has_audio": bool(audio_streams),
            "video": {
                "codec": primary_video.get("codec_name"),
                "width": primary_video.get("width"),
                "height": primary_video.get("height"),
                "avg_frame_rate": primary_video.get("avg_frame_rate"),
            }
            if primary_video
            else None,
            "streams": streams,
        }

    def _probe(
        self,
        *,
        project_id: str,
        offer: CapabilityOffer,
        payload: Mapping[str, Any],
    ) -> CapabilityExecutionResult:
        allowed = {"path"}
        unknown = set(payload).difference(allowed)
        if unknown:
            raise InvalidCapabilityInput(f"unsupported media.probe fields: {sorted(unknown)!r}")
        raw_path = payload.get("path")
        if not isinstance(raw_path, str):
            raise InvalidCapabilityInput("media.probe requires string field 'path'")
        canonical_path, source = self._resolve_input_file(
            project_id,
            raw_path,
            operation="media.probe",
        )
        output = self._probe_path(canonical_path=canonical_path, source=source)
        return CapabilityExecutionResult.from_offer(
            project_id=project_id,
            offer=offer,
            output=output,
        )

    def _extract_range(
        self,
        *,
        project_id: str,
        offer: CapabilityOffer,
        payload: Mapping[str, Any],
    ) -> CapabilityExecutionResult:
        allowed = {
            "source_path",
            "start_us",
            "end_us",
            "context_before_us",
            "context_after_us",
        }
        unknown = set(payload).difference(allowed)
        if unknown:
            raise InvalidCapabilityInput(
                f"unsupported video.extract_range fields: {sorted(unknown)!r}"
            )
        source_path = payload.get("source_path")
        if not isinstance(source_path, str):
            raise InvalidCapabilityInput("video.extract_range requires string field 'source_path'")
        try:
            requested = ProjectMediaRange(
                source_path=source_path,
                start_us=payload.get("start_us"),
                end_us=payload.get("end_us"),
                context_before_us=payload.get("context_before_us", 0),
                context_after_us=payload.get("context_after_us", 0),
            )
        except ProjectValidationError as exc:
            raise InvalidCapabilityInput(str(exc)) from exc

        canonical_source, source = self._resolve_input_file(
            project_id,
            requested.source_path,
            operation="video.extract_range",
        )
        probe = self._probe_path(canonical_path=canonical_source, source=source)
        if not probe["has_video"]:
            raise InvalidCapabilityInput("video.extract_range source does not contain a video stream")
        source_duration_us = probe.get("duration_us")
        if not isinstance(source_duration_us, int) or source_duration_us <= 0:
            raise InvalidCapabilityInput(
                "video.extract_range requires a source with a known positive duration"
            )
        try:
            resolved_range = requested.resolve(source_duration_us)
        except ProjectValidationError as exc:
            raise InvalidCapabilityInput(str(exc)) from exc

        segment_specs: list[tuple[str, int, int]] = []
        if resolved_range.before_duration_us > 0:
            segment_specs.append(
                ("context_before", resolved_range.context_start_us, resolved_range.start_us)
            )
        segment_specs.append(("requested", resolved_range.start_us, resolved_range.end_us))
        if resolved_range.after_duration_us > 0:
            segment_specs.append(
                ("context_after", resolved_range.end_us, resolved_range.context_end_us)
            )

        planned: list[tuple[str, int, int, str, str, Path]] = []
        for role, start_us, end_us in segment_specs:
            artifact_id = f"art_{uuid.uuid4().hex}"
            canonical_output = f"artifacts/{artifact_id}.mkv"
            try:
                output_path = self.store.resolve_project_file(
                    project_id,
                    canonical_output,
                    must_exist=False,
                    allowed_roots=_RANGE_OUTPUT_ROOTS,
                )
            except (ProjectValidationError, ProjectStoreError) as exc:
                raise InvalidCapabilityInput(str(exc)) from exc
            if output_path.exists() or output_path.is_symlink():
                raise InvalidCapabilityInput(
                    f"video.extract_range refuses to overwrite existing output: {canonical_output!r}"
                )
            planned.append((role, start_us, end_us, artifact_id, canonical_output, output_path))

        artifacts: list[ProjectReference] = []
        try:
            for role, start_us, end_us, artifact_id, canonical_output, output_path in planned:
                duration_us = end_us - start_us
                command = [
                    self._tool("ffmpeg"),
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-n",
                    "-ss",
                    f"{start_us}us",
                    "-i",
                    str(source),
                    "-t",
                    f"{duration_us}us",
                    "-map",
                    "0:v:0",
                    "-map",
                    "0:a?",
                    "-sn",
                    "-dn",
                    "-c:v",
                    "ffv1",
                    "-level",
                    "3",
                    "-c:a",
                    "flac",
                    str(output_path),
                ]
                self._invoke(command, timeout=self.extract_timeout_sec, tool="ffmpeg")
                try:
                    output_size = output_path.stat().st_size if output_path.is_file() else 0
                except OSError as exc:
                    raise CapabilityToolFailed(
                        "ffmpeg range output could not be validated"
                    ) from exc
                if output_size <= 0:
                    raise CapabilityToolFailed(
                        "ffmpeg reported success but range output is empty or missing"
                    )
                artifacts.append(
                    ProjectReference(
                        id=artifact_id,
                        kind="video",
                        path=canonical_output,
                        metadata={
                            "capability_id": offer.capability_id,
                            "offer_id": offer.offer_id,
                            "source_path": canonical_source,
                            "range_role": role,
                            "segment": {
                                "start_us": start_us,
                                "end_us": end_us,
                                "duration_us": duration_us,
                            },
                            "requested_range": requested.to_dict(),
                            "extraction_mode": _RANGE_EXTRACTION_MODE,
                        },
                    )
                )

            project = self.store.load_project(project_id)
            self.store.update_project(
                project_id,
                artifacts=(*project.artifacts, *artifacts),
            )
        except Exception:
            for *_, output_path in planned:
                output_path.unlink(missing_ok=True)
            raise

        by_role = {artifact.metadata["range_role"]: artifact for artifact in artifacts}
        requested_artifact = by_role["requested"]
        output = {
            "source_path": canonical_source,
            "range": resolved_range.to_dict(),
            "requested_path": requested_artifact.path,
            "context_before_path": (
                by_role["context_before"].path if "context_before" in by_role else None
            ),
            "context_after_path": (
                by_role["context_after"].path if "context_after" in by_role else None
            ),
            "artifact_paths": [artifact.path for artifact in artifacts],
            "extraction_mode": _RANGE_EXTRACTION_MODE,
        }
        return CapabilityExecutionResult.from_offer(
            project_id=project_id,
            offer=offer,
            output=output,
            artifact=requested_artifact.to_dict(),
        )

    def _assemble(
        self,
        *,
        project_id: str,
        offer: CapabilityOffer,
        payload: Mapping[str, Any],
    ) -> CapabilityExecutionResult:
        allowed = {"input_paths", "output_path"}
        unknown = set(payload).difference(allowed)
        if unknown:
            raise InvalidCapabilityInput(
                f"unsupported timeline.assemble fields: {sorted(unknown)!r}"
            )
        raw_inputs = payload.get("input_paths")
        raw_output = payload.get("output_path")
        if not isinstance(raw_inputs, list) or not raw_inputs:
            raise InvalidCapabilityInput("timeline.assemble requires non-empty input_paths array")
        if len(raw_inputs) > _MAX_CONCAT_INPUTS:
            raise InvalidCapabilityInput(
                f"timeline.assemble supports at most {_MAX_CONCAT_INPUTS} inputs"
            )
        if not isinstance(raw_output, str):
            raise InvalidCapabilityInput("timeline.assemble requires string output_path")

        input_paths: list[Path] = []
        canonical_inputs: list[str] = []
        for raw_path in raw_inputs:
            if not isinstance(raw_path, str):
                raise InvalidCapabilityInput("every timeline.assemble input path must be a string")
            canonical, resolved = self._resolve_input_file(
                project_id,
                raw_path,
                operation="timeline.assemble",
            )
            input_paths.append(resolved)
            canonical_inputs.append(canonical)

        canonical_output = _canonical_project_path(raw_output)
        try:
            output_path = self.store.resolve_project_file(
                project_id,
                canonical_output,
                must_exist=False,
                allowed_roots=_OUTPUT_ROOTS,
            )
        except (ProjectValidationError, ProjectStoreError) as exc:
            raise InvalidCapabilityInput(str(exc)) from exc
        if output_path.exists() or output_path.is_symlink():
            raise InvalidCapabilityInput(
                f"timeline.assemble refuses to overwrite existing output: {canonical_output!r}"
            )

        project_dir = self.store.project_directory(project_id)
        tasks_dir = project_dir / "tasks"
        manifest_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                prefix="ffconcat-",
                suffix=".txt",
                dir=tasks_dir,
                delete=False,
            ) as handle:
                manifest_path = Path(handle.name)
                for item in input_paths:
                    handle.write(_ffconcat_quote(item))

            command = [
                self._tool("ffmpeg"),
                "-hide_banner",
                "-loglevel",
                "error",
                "-n",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(manifest_path),
                "-c",
                "copy",
                "-movflags",
                "+faststart",
                str(output_path),
            ]
            self._invoke(command, timeout=self.assemble_timeout_sec, tool="ffmpeg")
            if not output_path.is_file():
                raise CapabilityToolFailed("ffmpeg reported success but output file was not created")

            artifact = ProjectReference(
                id=f"art_{uuid.uuid4().hex}",
                kind="video",
                path=canonical_output,
                metadata={
                    "capability_id": offer.capability_id,
                    "offer_id": offer.offer_id,
                    "input_paths": canonical_inputs,
                    "assembly_mode": "concat_copy",
                },
            )
            try:
                project = self.store.load_project(project_id)
                self.store.update_project(
                    project_id,
                    artifacts=(*project.artifacts, artifact),
                )
            except Exception:
                output_path.unlink(missing_ok=True)
                raise

            return CapabilityExecutionResult.from_offer(
                project_id=project_id,
                offer=offer,
                output={
                    "path": canonical_output,
                    "input_paths": canonical_inputs,
                    "assembly_mode": "concat_copy",
                },
                artifact=artifact.to_dict(),
            )
        finally:
            if manifest_path is not None:
                manifest_path.unlink(missing_ok=True)

    def _invoke(
        self,
        command: list[str],
        *,
        timeout: int,
        tool: str,
    ) -> subprocess.CompletedProcess[str]:
        try:
            completed = self.runner(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise CapabilityToolFailed(f"{tool} timed out after {timeout} seconds") from exc
        except OSError as exc:
            raise CapabilityToolUnavailable(f"could not start {tool}: {exc}") from exc
        if completed.returncode != 0:
            stderr = (completed.stderr or "").strip()
            if len(stderr) > 1200:
                stderr = stderr[-1200:]
            raise CapabilityToolFailed(
                f"{tool} failed with exit code {completed.returncode}: {stderr or 'no error output'}"
            )
        return completed
