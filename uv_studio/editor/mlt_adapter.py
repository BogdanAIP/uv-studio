"""Bounded MLT timeline projection behind the UV Studio canonical editor state."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any

from uv_studio.projects.edit_state import RangeEditStateStore
from uv_studio.projects.models import ProjectReference, ProjectValidationError
from uv_studio.projects.store import ProjectNotFound, ProjectStore, ProjectStoreError

_MICROSECONDS_PER_SECOND = 1_000_000
_INPUT_ROOTS = ("sources", "assets", "artifacts", "exports")


class MLTAdapterError(ProjectValidationError):
    """Canonical project state cannot be projected safely into MLT."""


@dataclass(frozen=True)
class MLTProjectionSegment:
    role: str
    project_path: str
    producer_id: str
    in_frame: int
    out_frame: int
    edit_id: str | None = None

    @property
    def frame_count(self) -> int:
        return self.out_frame - self.in_frame + 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "project_path": self.project_path,
            "in_frame": self.in_frame,
            "out_frame": self.out_frame,
            "frame_count": self.frame_count,
            "edit_id": self.edit_id,
        }


@dataclass(frozen=True)
class MLTTimelineProjection:
    source_path: str
    frame_rate_num: int
    frame_rate_den: int
    width: int
    height: int
    source_duration_us: int
    accepted_edit_ids: tuple[str, ...]
    segments: tuple[MLTProjectionSegment, ...]
    max_boundary_error_us: int
    xml_text: str

    @property
    def exact_boundaries(self) -> bool:
        return self.max_boundary_error_us == 0

    def to_summary(self) -> dict[str, Any]:
        return {
            "source_path": self.source_path,
            "frame_rate": f"{self.frame_rate_num}/{self.frame_rate_den}",
            "width": self.width,
            "height": self.height,
            "source_duration_us": self.source_duration_us,
            "accepted_edit_ids": list(self.accepted_edit_ids),
            "segment_count": len(self.segments),
            "segments": [segment.to_dict() for segment in self.segments],
            "exact_boundaries": self.exact_boundaries,
            "max_boundary_error_us": self.max_boundary_error_us,
        }


def _positive_int(metadata: dict[str, Any], key: str) -> int:
    value = metadata.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise MLTAdapterError(f"source metadata requires positive integer {key}")
    return value


def _frame_rate(metadata: dict[str, Any]) -> Fraction:
    raw = metadata.get("avg_frame_rate")
    if not isinstance(raw, str) or not raw.strip():
        raise MLTAdapterError("source metadata requires avg_frame_rate for MLT projection")
    try:
        rate = Fraction(raw.strip())
    except (ValueError, ZeroDivisionError) as exc:
        raise MLTAdapterError("source avg_frame_rate is invalid") from exc
    if rate <= 0 or rate > 1000:
        raise MLTAdapterError("source avg_frame_rate is outside supported bounds")
    return rate


def _boundary_frame(time_us: int, rate: Fraction) -> int:
    return round(Fraction(time_us, _MICROSECONDS_PER_SECOND) * rate)


def _boundary_error_us(time_us: int, frame: int, rate: Fraction) -> int:
    represented = Fraction(frame * _MICROSECONDS_PER_SECOND, 1) / rate
    return round(abs(represented - time_us))


def _add_property(parent: ET.Element, name: str, value: str) -> None:
    node = ET.SubElement(parent, "property", {"name": name})
    node.text = value


class MLTTimelineAdapter:
    """Project canonical UV range edits into an internal MLT XML representation.

    The XML may contain resolved host paths because it is an ephemeral engine input.
    It is never canonical project state and is never returned by the public editor API.
    """

    adapter_id = "mlt"

    def __init__(self, project_store: ProjectStore, *, melt_path: str | None = None) -> None:
        self.project_store = project_store
        self.melt_path = melt_path

    def runtime_path(self) -> str | None:
        return self.melt_path or shutil.which("melt") or shutil.which("melt.exe")

    def runtime_available(self) -> bool:
        return self.runtime_path() is not None

    def _source_reference(self, project_id: str, source_path: str) -> ProjectReference:
        project = self.project_store.load_project(project_id)
        reference = next(
            (item for item in project.sources if item.kind == "video" and item.path == source_path),
            None,
        )
        if reference is None:
            raise MLTAdapterError(f"MLT projection source is not a registered video source: {source_path!r}")
        return reference

    def _resolve(self, project_id: str, project_path: str) -> Path:
        try:
            path = self.project_store.resolve_project_file(
                project_id,
                project_path,
                must_exist=True,
                allowed_roots=_INPUT_ROOTS,
            )
        except (ProjectValidationError, ProjectStoreError) as exc:
            raise MLTAdapterError(str(exc)) from exc
        if not path.is_file() or path.is_symlink():
            raise MLTAdapterError(f"MLT input must be a regular project file: {project_path!r}")
        return path

    def project_timeline(self, project_id: str, source_path: str) -> MLTTimelineProjection:
        source_reference = self._source_reference(project_id, source_path)
        metadata = source_reference.metadata
        width = _positive_int(metadata, "width")
        height = _positive_int(metadata, "height")
        duration_us = _positive_int(metadata, "duration_us")
        rate = _frame_rate(metadata)
        source_absolute = self._resolve(project_id, source_reference.path)
        state = RangeEditStateStore(self.project_store).load(project_id)
        edits = state.for_source(source_reference.path)

        source_frames = _boundary_frame(duration_us, rate)
        if source_frames <= 0:
            raise MLTAdapterError("MLT source duration maps to zero frames")

        root = ET.Element("mlt", {"LC_NUMERIC": "C"})
        gcd_width_height = __import__("math").gcd(width, height)
        ET.SubElement(
            root,
            "profile",
            {
                "description": "UV Studio MLT derived projection",
                "width": str(width),
                "height": str(height),
                "progressive": "1",
                "sample_aspect_num": "1",
                "sample_aspect_den": "1",
                "display_aspect_num": str(width // gcd_width_height),
                "display_aspect_den": str(height // gcd_width_height),
                "frame_rate_num": str(rate.numerator),
                "frame_rate_den": str(rate.denominator),
                "colorspace": "709",
            },
        )
        source_producer = ET.SubElement(
            root,
            "producer",
            {"id": "uv_source", "in": "0", "out": str(source_frames - 1)},
        )
        _add_property(source_producer, "mlt_service", "avformat-novalidate")
        _add_property(source_producer, "resource", source_absolute.as_posix())

        playlist = ET.SubElement(root, "playlist", {"id": "uv_playlist0"})
        segments: list[MLTProjectionSegment] = []
        boundary_errors: list[int] = []
        cursor_frame = 0

        for index, edit in enumerate(edits, start=1):
            start_frame = _boundary_frame(edit.start_us, rate)
            end_frame = _boundary_frame(edit.end_us, rate)
            boundary_errors.extend(
                [
                    _boundary_error_us(edit.start_us, start_frame, rate),
                    _boundary_error_us(edit.end_us, end_frame, rate),
                ]
            )
            if start_frame < cursor_frame or end_frame <= start_frame or end_frame > source_frames:
                raise MLTAdapterError(
                    f"accepted edit {edit.edit_id!r} cannot be represented as an ordered MLT frame range"
                )
            if start_frame > cursor_frame:
                ET.SubElement(
                    playlist,
                    "entry",
                    {"producer": "uv_source", "in": str(cursor_frame), "out": str(start_frame - 1)},
                )
                segments.append(
                    MLTProjectionSegment(
                        role="source",
                        project_path=source_reference.path,
                        producer_id="uv_source",
                        in_frame=cursor_frame,
                        out_frame=start_frame - 1,
                    )
                )

            replacement_absolute = self._resolve(project_id, edit.replacement_path)
            replacement_id = f"uv_replacement_{index}"
            replacement_frames = end_frame - start_frame
            replacement_producer = ET.SubElement(
                root,
                "producer",
                {"id": replacement_id, "in": "0", "out": str(replacement_frames - 1)},
            )
            _add_property(replacement_producer, "mlt_service", "avformat-novalidate")
            _add_property(replacement_producer, "resource", replacement_absolute.as_posix())
            ET.SubElement(
                playlist,
                "entry",
                {
                    "producer": replacement_id,
                    "in": "0",
                    "out": str(replacement_frames - 1),
                    "uv_edit_id": edit.edit_id,
                },
            )
            segments.append(
                MLTProjectionSegment(
                    role="replacement",
                    project_path=edit.replacement_path,
                    producer_id=replacement_id,
                    in_frame=0,
                    out_frame=replacement_frames - 1,
                    edit_id=edit.edit_id,
                )
            )
            cursor_frame = end_frame

        if cursor_frame < source_frames:
            ET.SubElement(
                playlist,
                "entry",
                {"producer": "uv_source", "in": str(cursor_frame), "out": str(source_frames - 1)},
            )
            segments.append(
                MLTProjectionSegment(
                    role="source",
                    project_path=source_reference.path,
                    producer_id="uv_source",
                    in_frame=cursor_frame,
                    out_frame=source_frames - 1,
                )
            )

        tractor = ET.SubElement(
            root,
            "tractor",
            {"id": "uv_tractor0", "in": "0", "out": str(source_frames - 1)},
        )
        ET.SubElement(tractor, "track", {"producer": "uv_playlist0"})
        xml_text = ET.tostring(root, encoding="unicode")
        return MLTTimelineProjection(
            source_path=source_reference.path,
            frame_rate_num=rate.numerator,
            frame_rate_den=rate.denominator,
            width=width,
            height=height,
            source_duration_us=duration_us,
            accepted_edit_ids=tuple(edit.edit_id for edit in edits),
            segments=tuple(segments),
            max_boundary_error_us=max(boundary_errors, default=0),
            xml_text=xml_text,
        )

    def project_summary(self, project_id: str) -> dict[str, Any]:
        try:
            project = self.project_store.load_project(project_id)
        except ProjectNotFound:
            raise
        timelines: list[dict[str, Any]] = []
        for source in project.sources:
            if source.kind != "video":
                continue
            try:
                timelines.append({"status": "ready", **self.project_timeline(project_id, source.path).to_summary()})
            except (MLTAdapterError, ProjectStoreError) as exc:
                timelines.append(
                    {
                        "status": "projection_error",
                        "source_path": source.path,
                        "error": str(exc),
                    }
                )
        return {
            "adapter_id": self.adapter_id,
            "runtime_available": self.runtime_available(),
            "timelines": timelines,
        }

    def render_projection(self, projection: MLTTimelineProjection, output_path: Path) -> Path:
        melt = self.runtime_path()
        if melt is None:
            raise MLTAdapterError("melt runtime is not available")
        output = Path(output_path).resolve()
        if output.exists():
            raise MLTAdapterError("MLT projection render refuses to overwrite output")
        output.parent.mkdir(parents=True, exist_ok=True)
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                suffix=".mlt",
                prefix="uv-mlt-",
                dir=output.parent,
                delete=False,
            ) as handle:
                handle.write(projection.xml_text)
                temp_path = Path(handle.name)
            completed = subprocess.run(
                [
                    melt,
                    str(temp_path),
                    "-consumer",
                    f"avformat:{output}",
                    "vcodec=ffv1",
                    "an=1",
                    "real_time=-1",
                    "terminate_on_pause=1",
                ],
                cwd=str(Path(melt).resolve().parent),
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
                shell=False,
            )
            if completed.returncode != 0 or not output.is_file() or output.stat().st_size <= 0:
                output.unlink(missing_ok=True)
                tail = (completed.stdout or "")[-1600:]
                raise MLTAdapterError(
                    f"melt failed to render derived projection: {tail or 'no output'}"
                )
            return output
        except subprocess.TimeoutExpired as exc:
            output.unlink(missing_ok=True)
            raise MLTAdapterError("melt projection render timed out") from exc
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
