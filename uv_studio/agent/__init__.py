"""Bounded UV-owned Agent Harness foundation and D-066 orchestration layers."""

from .background import (
    AGENT_BACKGROUND_LEASE_SCHEMA_VERSION,
    MAX_BACKGROUND_CLAIMS_PER_TASK,
    MAX_BACKGROUND_TASK_BUDGET,
    AgentBackgroundClaim,
    AgentBackgroundContextStale,
    AgentBackgroundError,
    AgentBackgroundLeaseConflict,
    AgentBackgroundLeaseRecord,
    AgentBackgroundLeaseStale,
    AgentBackgroundLeaseStore,
    AgentBackgroundRetryLimit,
    AgentBackgroundTaskCoordinator,
    AgentBackgroundWorker,
)
from .harness import AgentActionCatalog, AgentContextBuilder, AgentHarness, AgentTraceStore
from .models import (
    AgentActionDefinition,
    AgentContextSnapshot,
    AgentHarnessError,
    AgentPolicyProjection,
    AgentPortableStateError,
    AgentTraceRecord,
    AgentTraceStatus,
    AgentUnknownAction,
)
from .orchestration import (
    AgentPlanRecord,
    AgentPlanStatus,
    AgentPlanStepProposal,
    AgentPlanningError,
    AgentSkillDefinition,
    AgentSkillError,
    AgentTaskBlocked,
    AgentTaskRecord,
    AgentTaskSpec,
    AgentTaskStateError,
    AgentTaskStatus,
)
from .stage16_runtime import (
    AGENT_SKILL_SCHEMA_VERSION,
    AgentPlanExecutionState,
    AgentPlanStore,
    AgentSkillCatalog,
)
from .stage16_generation_target import (
    AgentPlanner,
    AgentTaskCoordinator as _ForegroundAgentTaskCoordinator,
    AgentTaskStore,
)
from .subagents import (
    AGENT_SUBAGENT_SCHEMA_VERSION,
    AgentSubagentCatalog,
    AgentSubagentContext,
    AgentSubagentDefinition,
    AgentSubagentError,
    AgentSubagentFinding,
    AgentSubagentFindingSeverity,
    AgentSubagentProposer,
    AgentSubagentRequest,
    AgentSubagentRole,
)
from .stage17_provenance import (
    AgentSubagentCoordinator,
    AgentSubagentResult,
    AgentSubagentTaskCoordinator as _ForegroundAgentSubagentTaskCoordinator,
)

_BACKGROUND_OWNER_ATTR = "_uv_agent_background_task_coordinator_owner"


def _reject_background_owned_harness(harness) -> None:
    if getattr(harness, _BACKGROUND_OWNER_ATTR, None) is not None:
        raise AgentTaskStateError(
            "AgentHarness is owned by an AgentBackgroundTaskCoordinator"
        )


class AgentTaskCoordinator(_ForegroundAgentTaskCoordinator):
    """Public foreground coordinator that cannot replace Stage-18 background fences."""

    def __init__(self, harness, **kwargs) -> None:
        _reject_background_owned_harness(harness)
        super().__init__(harness, **kwargs)


class AgentSubagentTaskCoordinator(_ForegroundAgentSubagentTaskCoordinator):
    """Public Stage-17 foreground coordinator with the same background ownership guard."""

    def __init__(self, harness, **kwargs) -> None:
        _reject_background_owned_harness(harness)
        super().__init__(harness, **kwargs)


__all__ = [
    "AGENT_BACKGROUND_LEASE_SCHEMA_VERSION",
    "AGENT_SKILL_SCHEMA_VERSION",
    "AGENT_SUBAGENT_SCHEMA_VERSION",
    "MAX_BACKGROUND_CLAIMS_PER_TASK",
    "MAX_BACKGROUND_TASK_BUDGET",
    "AgentActionCatalog",
    "AgentActionDefinition",
    "AgentBackgroundClaim",
    "AgentBackgroundContextStale",
    "AgentBackgroundError",
    "AgentBackgroundLeaseConflict",
    "AgentBackgroundLeaseRecord",
    "AgentBackgroundLeaseStale",
    "AgentBackgroundLeaseStore",
    "AgentBackgroundRetryLimit",
    "AgentBackgroundTaskCoordinator",
    "AgentBackgroundWorker",
    "AgentContextBuilder",
    "AgentContextSnapshot",
    "AgentHarness",
    "AgentHarnessError",
    "AgentPlanExecutionState",
    "AgentPlanRecord",
    "AgentPlanStatus",
    "AgentPlanStepProposal",
    "AgentPlanStore",
    "AgentPlanner",
    "AgentPlanningError",
    "AgentPolicyProjection",
    "AgentPortableStateError",
    "AgentSkillCatalog",
    "AgentSkillDefinition",
    "AgentSkillError",
    "AgentSubagentCatalog",
    "AgentSubagentContext",
    "AgentSubagentCoordinator",
    "AgentSubagentDefinition",
    "AgentSubagentError",
    "AgentSubagentFinding",
    "AgentSubagentFindingSeverity",
    "AgentSubagentProposer",
    "AgentSubagentRequest",
    "AgentSubagentResult",
    "AgentSubagentRole",
    "AgentSubagentTaskCoordinator",
    "AgentTaskBlocked",
    "AgentTaskCoordinator",
    "AgentTaskRecord",
    "AgentTaskSpec",
    "AgentTaskStateError",
    "AgentTaskStatus",
    "AgentTaskStore",
    "AgentTraceRecord",
    "AgentTraceStatus",
    "AgentTraceStore",
    "AgentUnknownAction",
]
