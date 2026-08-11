"""Execute exact MCP bindings behind UV Studio authorization and provenance."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from uv_studio.mcp.manager import MCPManager
from uv_studio.projects.models import ProjectValidationError
from uv_studio.projects.store import ProjectNotFound, ProjectStore, ProjectStoreError
from uv_studio.projects.task_records import ProjectTaskRecordStore

from ..authorization import ExecutionPreparation
from ..execution import CapabilityExecutionResult
from ..models import CapabilityOffer
from ..provenance import ExternalRunProvenance

_WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:[\\/]")


class MCPExecutionInputRejected(ValueError):
    code = "mcp_unsafe_file_argument"


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
            target=target,
        )
        try:
            # Reject caller-supplied host paths before any trusted translation occurs.
            self._reject_raw_host_paths(payload)
            arguments = self._translate_project_file_inputs(
                project_id=project_id,
                binding=target.binding,
                payload=payload,
            )
            mcp_result = await self.manager.invoke_target(target, arguments)
        except Exception as exc:
            self.provenance.fail(record, exc)
            raise

        self.provenance.succeed(record, mcp_result)
        return CapabilityExecutionResult.from_offer(
            project_id=project_id,
            offer=offer,
            output={
                "run_id": record.run_id,
                "mcp_result": mcp_result,
            },
        )

    def _translate_project_file_inputs(self, *, project_id, binding, payload) -> dict[str, Any]:
        """Translate only explicitly declared top-level project file arguments.

        Authorization/provenance stay bound to the original portable payload. Absolute
        paths exist only in this short-lived invocation dictionary.
        """
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
            if not resolved.is_file():
                raise MCPExecutionInputRejected(
                    f"project-file argument {spec.argument_name!r} must resolve to a file"
                )
            translated[spec.argument_name] = str(resolved)
        return translated

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
