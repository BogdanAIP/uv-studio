"""Public Stage-18 background execution API with stable harness fence ownership.

The implementation lives in ``_background_impl``.  This public seam adds the
one-coordinator-per-AgentHarness invariant required to keep the installed
ProjectUnitOfWork / Generation fences bound to the coordinator that owns them.
"""

from __future__ import annotations

from . import _background_impl as _impl
from ._background_impl import *  # noqa: F401,F403


class AgentBackgroundTaskCoordinator(_impl.AgentBackgroundTaskCoordinator):
    """Own the background fences installed into exactly one AgentHarness."""

    def __init__(
        self,
        harness,
        *,
        planner=None,
        plan_store=None,
        task_store=None,
        clock=_impl._utc_now,
    ) -> None:
        production = getattr(harness, "production", None)
        timeline = getattr(harness, "timeline", None)
        generation = getattr(harness, "generation", None)
        if (
            isinstance(
                getattr(production, "uow", None),
                _impl._BackgroundFencedProjectUnitOfWork,
            )
            or isinstance(
                getattr(timeline, "unit_of_work", None),
                _impl._BackgroundFencedProjectUnitOfWork,
            )
            or isinstance(generation, _impl._BackgroundFencedGenerationService)
        ):
            raise AgentBackgroundError(
                "AgentHarness already has an AgentBackgroundTaskCoordinator"
            )
        super().__init__(
            harness,
            planner=planner,
            plan_store=plan_store,
            task_store=task_store,
            clock=clock,
        )


__all__ = list(_impl.__all__)
