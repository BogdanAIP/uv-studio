"""Crash-safe arbitrary-path timeline assembly over the existing FFmpeg adapter."""

from __future__ import annotations

import os
import tempfile
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from uv_studio.projects.models import ProjectReference, ProjectValidationError
from uv_studio.projects.publication import (
    begin_managed_publication,
    finish_managed_publication,
)
from uv_studio.projects.store import ProjectStoreError
from uv_studio.projects.task_records import ProjectTaskRecordStore

from ..execution import CapabilityExecutionResult, CapabilityToolFailed, InvalidCapabilityInput
from ..models import CapabilityOffer
from .local_ffmpeg import (
    _MAX_CONCAT_INPUTS,
    _OUTPUT_ROOTS,
    _canonical_project_path,
    _ffconcat_quote,
)
from .range_reinsertion import LocalFFmpegRangeAdapter


class CrashSafeLocalFFmpegRangeAdapter(LocalFFmpegRangeAdapter):
    """Range adapter whose ``timeline.assemble`` survives process-loss boundaries.

    Rendering still happens outside the project fence. Immediately before the final
    arbitrary-path byte move, a durable marker is written inside the same shared
    project lock. Normal completion removes it before unlocking. If the process dies,
    startup recovery/archive can distinguish that path from ordinary portable files.
    """

    @staticmethod
    def _finish_marker_best_effort(store, project_id: str, publication_id: str | None) -> None:
        if publication_id is None:
            return
        try:
            finish_managed_publication(store, project_id, publication_id)
        except Exception:
            # Leaving a marker is fail-closed: archive will reject it and startup
            # recovery can reconcile it later. Never hide the original publisher error.
            pass

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

        artifact_id = f"art_{uuid.uuid4().hex}"
        manifest_path: Path | None = None
        staged_output: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                prefix=".uv-ffconcat-",
                suffix=".txt",
                dir=self.store.root,
                delete=False,
            ) as handle:
                manifest_path = Path(handle.name)
                for item in input_paths:
                    handle.write(_ffconcat_quote(item))

            with tempfile.NamedTemporaryFile(
                prefix=f".uv-timeline-assemble-{artifact_id}-",
                suffix=output_path.suffix,
                dir=self.store.root,
                delete=False,
            ) as handle:
                staged_output = Path(handle.name)
            staged_output.unlink()

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
                str(staged_output),
            ]
            self._invoke(command, timeout=self.assemble_timeout_sec, tool="ffmpeg")
            if staged_output.is_symlink() or not staged_output.is_file():
                raise CapabilityToolFailed("ffmpeg reported success but output file was not created")
            try:
                output_size = staged_output.stat().st_size
            except OSError as exc:
                raise CapabilityToolFailed("ffmpeg output could not be validated") from exc
            if output_size <= 0:
                raise CapabilityToolFailed("ffmpeg reported success but output file is empty")

            artifact = ProjectReference(
                id=artifact_id,
                kind="video",
                path=canonical_output,
                metadata={
                    "capability_id": offer.capability_id,
                    "offer_id": offer.offer_id,
                    "input_paths": canonical_inputs,
                    "assembly_mode": "concat_copy",
                },
            )

            # Long-running FFmpeg work stays outside the canonical project tree. The
            # marker exists only inside the final shared critical section, immediately
            # before bytes can become canonical.
            with ProjectTaskRecordStore(self.store).project_lock(project_id):
                try:
                    fenced_output = self.store.resolve_project_file(
                        project_id,
                        canonical_output,
                        must_exist=False,
                        allowed_roots=_OUTPUT_ROOTS,
                    )
                except (ProjectValidationError, ProjectStoreError) as exc:
                    raise InvalidCapabilityInput(str(exc)) from exc
                if fenced_output.exists() or fenced_output.is_symlink():
                    raise InvalidCapabilityInput(
                        f"timeline.assemble refuses to overwrite existing output: {canonical_output!r}"
                    )

                publication_id = begin_managed_publication(
                    self.store,
                    project_id,
                    relative_path=canonical_output,
                    purpose="timeline.assemble",
                    reference_id=artifact_id,
                )
                final_written = False
                try:
                    os.replace(staged_output, fenced_output)
                    final_written = True
                    project = self.store.load_project(project_id)
                    self.store.update_project(
                        project_id,
                        artifacts=(*project.artifacts, artifact),
                    )
                    finish_managed_publication(self.store, project_id, publication_id)
                except Exception:
                    if final_written:
                        try:
                            current = self.store.load_project(project_id)
                            registered = any(item.id == artifact_id for item in current.artifacts)
                        except Exception:
                            # Ambiguous post-crash-like state: preserve both bytes and
                            # marker. Recovery/archive will resolve or fail closed.
                            registered = None
                        if registered is False:
                            fenced_output.unlink(missing_ok=True)
                            self._finish_marker_best_effort(
                                self.store, project_id, publication_id
                            )
                        elif registered is True:
                            self._finish_marker_best_effort(
                                self.store, project_id, publication_id
                            )
                    else:
                        # No canonical bytes crossed the boundary, so clearing the
                        # prepared marker is an unambiguous rollback.
                        self._finish_marker_best_effort(self.store, project_id, publication_id)
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
            if staged_output is not None:
                staged_output.unlink(missing_ok=True)
