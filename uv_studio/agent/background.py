"""Public Stage-18 background execution API with stable harness fence ownership.

The implementation lives in ``_background_impl``.  This public seam adds the
one-coordinator-per-AgentHarness invariant required to keep the installed
ProjectUnitOfWork / Generation fences bound to the coordinator that owns them.
"""

from __future__ import annotations

import threading

from . import _background_impl as _impl
from ._background_impl import *  # noqa: F401,F403


_BACKGROUND_OWNER_ATTR = "_uv_agent_background_task_coordinator_owner"
_BACKGROUND_OWNER_PENDING = object()
_BACKGROUND_OWNER_GUARD = threading.RLock()


def _reserve_background_owner(harness) -> None:
    """Atomically reserve one harness before any background fence is installed."""

    with _BACKGROUND_OWNER_GUARD:
        production = getattr(harness, "production", None)
        timeline = getattr(harness, "timeline", None)
        generation = getattr(harness, "generation", None)
        if (
            getattr(harness, _BACKGROUND_OWNER_ATTR, None) is not None
            or isinstance(
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
        setattr(harness, _BACKGROUND_OWNER_ATTR, _BACKGROUND_OWNER_PENDING)


def _release_failed_background_reservation(harness) -> None:
    with _BACKGROUND_OWNER_GUARD:
        if getattr(harness, _BACKGROUND_OWNER_ATTR, None) is _BACKGROUND_OWNER_PENDING:
            delattr(harness, _BACKGROUND_OWNER_ATTR)


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
        _reserve_background_owner(harness)
        try:
            super().__init__(
                harness,
                planner=planner,
                plan_store=plan_store,
                task_store=task_store,
                clock=clock,
            )
        except BaseException:
            _release_failed_background_reservation(harness)
            raise

        with _BACKGROUND_OWNER_GUARD:
            if getattr(harness, _BACKGROUND_OWNER_ATTR, None) is not _BACKGROUND_OWNER_PENDING:
                raise AgentBackgroundError(
                    "AgentHarness background coordinator ownership reservation changed"
                )
            setattr(harness, _BACKGROUND_OWNER_ATTR, self)


__all__ = list(_impl.__all__)
