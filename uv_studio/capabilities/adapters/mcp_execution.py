"""Execute exact MCP bindings behind UV Studio authorization and provenance."""

from __future__ import annotations

import re
import uuid
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from uv_studio.mcp.client import MCPCallError
from uv_studio.mcp.manager import MCPManager
from uv_studio.projects.models import ProjectReference, ProjectValidationError
from uv_studio.projects.store import ProjectNotFound, ProjectStore, ProjectStoreError
from uv_studio.projects.task_records import ProjectTaskRecordStore

from ..authorization import ExecutionPreparation
from ..execution import CapabilityExecutionResult
from ..models import CapabilityOffer
from ..provenance import ExternalExecutionTarget, ExternalRunProvenance

_WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:[\\/]")


class MCPExecutionInputRejected(ValueError):
    code = "mcp_unsafe_file_argument"


class MCPExecutionOutputRejected(MCPCallError):
    code = "mcp_invalid_project_output"


class MCPExecutionAdapter:
    def __init__(self, manager: MCPManager, project_store: ProjectStore) -> None:
        self.manager = manager
        self.project_store = project_store
        self.provenance = ExternalRunProvenance(ProjectTaskRecordStore(project_store))

    async def execute(
        self,
        *,
        project_id: str,
        offer: CapabilityOffer,
        preparation: ExecutionPreparation,
        payload: Mapping[str, Any],
    ) -> CapabilityExecutionResult:
        target = self.manager.resolve_execution_target(offer)
        record = self.provenance.start(
            project_id=project_id,
            offer=offer,
            preparation=preparation,
            target=ExternalExecutionTarget(
                profile_id=target.profile.profile_id,
                tool_name=target.binding.tool_name,
            ),
        )
        allocated_outputs: list[tuple[Any, str, Path, str]] = []
        registered_ids: tuple[str, ...] = ()
        try:
            self._reject_raw_host_paths(payload)
            arguments = self._translate_project_file_inputs(
                project_id=project_id,
                binding=target.binding,
                payload=payload,
            )
            allocated_outputs = self._inject_project_file_outputs(
                project_id=project_id,
                binding=target.binding,
                arguments=arguments,
            )
            mcp_result = await self.manager.invoke_target(target, arguments)
            references = self._validate_output_files(
                project_id=project_id,
                offer=offer,
                run_id=record.run_id,
                allocated_outputs=allocated_outputs,
            )
            if references:
                project = self.project_store.load_project(project_id)
                self.project_store.update_project(
                    project_id,
                    artifacts=(*project.artifacts, *references),
                )
                registered_ids = tuple(item.id for item in references)
            self.provenance.succeed(record, mcp_result)
        except Exception as exc:
            self._rollback_outputs(
                project_id=project_id,
                allocated_outputs=allocated_outputs,
                registered_ids=registered_ids,
            )
            self.provenance.fail(record, exc)
            raise

        artifact_dicts = [item.to_dict() for item in references]
        return CapabilityExecutionResult.from_offer(
            project_id=project_id,
            offer=offer,
            output={
                "run_id": record.run_id,
                "mcp_result": mcp_result,
                "artifacts": artifact_dicts,
            },
            artifact=(artifact_dicts[0] if artifact_dicts else None),
        )

    def _translate_project_file_inputs(
        self,
        *,
        project_id,
        binding,
        payload,
    ) -> dict[str, Any]:
        """Translate only explicitly declared top-level project file arguments."""
        translated = dict(payload)
        for spec in binding.project_file_inputs:
            if spec.argument_name not in translated:
                if spec.required:
                    raise MCPExecutionInputRejected(
                        f"required project-file argument {spec.argument_name!r} is missing"
                    )
                continue
            value = translated[spec.argument_name]
            if not isinstance(value, str) or not value.strip():
                raise MCPExecutionInputRejected(
                    f"project-file argument {spec.argument_name!r} must be a project-relative string"
                )
            try:
                resolved = self.project_store.resolve_project_file(
                    project_id,
                    value,
                    must_exist=True,
                    allowed_roots=spec.allowed_roots,
                )
            except (ProjectValidationError, ProjectNotFound, ProjectStoreError) as exc:
                raise MCPExecutionInputRejected(
                    f"project-file argument {spec.argument_name!r} is not an allowed existing project file"
                ) from exc
            if not resolved.is_file() or resolved.is_symlink():
                raise MCPExecutionInputRejected(
                    f"project-file argument {spec.argument_name!r} must resolve to a regular file"
                )
            translated[spec.argument_name] = str(resolved)
        return translated

    def _inject_project_file_outputs(
        self,
        *,
        project_id: str,
        binding,
        arguments: dict[str, Any],
    ) -> list[tuple[Any, str, Path, str]]:
        """Allocate binding-owned output arguments under canonical project artifacts."""
        allocated: list[tuple[Any, str, Path, str]] = []
        for spec in binding.project_file_outputs:
            if spec.argument_name in arguments:
                raise MCPExecutionInputRejected(
                    f"project output argument {spec.argument_name!r} is binding-owned and cannot be caller supplied"
                )
            artifact_id = f"art_{uuid.uuid4().hex}"
            relative_path = f"artifacts/{artifact_id}{spec.suffix}"
            try:
                output_path = self.project_store.resolve_project_file(
                    project_id,
                    relative_path,
                    must_exist=False,
                    allowed_roots=("artifacts",),
                )
            except (ProjectValidationError, ProjectNotFound, ProjectStoreError) as exc:
                raise MCPExecutionOutputRejected(
                    f"could not allocate project output for {spec.argument_name!r}"
                ) from exc
            if output_path.exists() or output_path.is_symlink():
                raise MCPExecutionOutputRejected("allocated MCP project output already exists")
            arguments[spec.argument_name] = str(output_path)
            allocated.append((spec, artifact_id, output_path, relative_path))
        return allocated

    def _validate_output_files(
        self,
        *,
        project_id: str,
        offer: CapabilityOffer,
        run_id: str,
        allocated_outputs: list[tuple[Any, str, Path, str]],
    ) -> tuple[ProjectReference, ...]:
        references: list[ProjectReference] = []
        for spec, artifact_id, allocated_path, relative_path in allocated_outputs:
            if not allocated_path.exists() and not allocated_path.is_symlink():
                if spec.required:
                    raise MCPExecutionOutputRejected(
                        f"required MCP project output {spec.argument_name!r} was not produced"
                    )
                continue
            if allocated_path.is_symlink():
                raise MCPExecutionOutputRejected(
                    f"MCP project output {spec.argument_name!r} must not be a symlink"
                )
            try:
                resolved = self.project_store.resolve_project_file(
                    project_id,
                    relative_path,
                    must_exist=True,
                    allowed_roots=("artifacts",),
                )
            except (ProjectValidationError, ProjectNotFound, ProjectStoreError) as exc:
                raise MCPExecutionOutputRejected(
                    f"MCP project output {spec.argument_name!r} escaped its allocated project path"
                ) from exc
            if not resolved.is_file() or resolved.is_symlink():
                raise MCPExecutionOutputRejected(
                    f"MCP project output {spec.argument_name!r} must be a regular file"
                )
            if resolved.stat().st_size <= 0:
                raise MCPExecutionOutputRejected(
                    f"MCP project output {spec.argument_name!r} must not be empty"
                )
            references.append(
                ProjectReference(
                    id=artifact_id,
                    kind=spec.media_kind.value,
                    path=relative_path,
                    metadata={
                        "lifecycle": "external_output",
                        "capability_id": offer.capability_id,
                        "run_id": run_id,
                    },
                )
            )
        return tuple(references)

    def _rollback_outputs(
        self,
        *,
        project_id: str,
        allocated_outputs: list[tuple[Any, str, Path, str]],
        registered_ids: tuple[str, ...],
    ) -> None:
        if registered_ids:
            try:
                project = self.project_store.load_project(project_id)
                self.project_store.update_project(
                    project_id,
                    artifacts=tuple(
                        item for item in project.artifacts if item.id not in set(registered_ids)
                    ),
                )
            except Exception:
                pass
        for _spec, _artifact_id, path, _relative_path in allocated_outputs:
            try:
                if path.is_symlink() or path.is_file():
                    path.unlink()
            except OSError:
                pass

    @classmethod
    def _reject_raw_host_paths(cls, value: Any) -> None:
        if isinstance(value, str):
            stripped = value.strip()
            lowered = stripped.lower()
            if (
                stripped.startswith("/")
                or stripped.startswith("\\\\")
                or _WINDOWS_ABSOLUTE_RE.match(stripped)
                or lowered.startswith("file://")
            ):
                raise MCPExecutionInputRejected(
                    "raw host filesystem paths are not allowed in MCP arguments"
                )
            return
        if isinstance(value, Mapping):
            for item in value.values():
                cls._reject_raw_host_paths(item)
            return
        if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
            for item in value:
                cls._reject_raw_host_paths(item)
