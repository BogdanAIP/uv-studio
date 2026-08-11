"""Execute exact MCP bindings behind UV Studio authorization and provenance."""

from __future__ import annotations

from typing import Any, Mapping

from uv_studio.mcp.manager import MCPManager
from uv_studio.projects.store import ProjectStore
from uv_studio.projects.task_records import ProjectTaskRecordStore

from ..authorization import ExecutionPreparation
from ..execution import CapabilityExecutionResult
from ..models import CapabilityOffer
from ..provenance import ExternalRunProvenance


class MCPExecutionAdapter:
    def __init__(self, manager: MCPManager, project_store: ProjectStore) -> None:
        self.manager = manager
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
            mcp_result = await self.manager.invoke_target(target, payload)
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
