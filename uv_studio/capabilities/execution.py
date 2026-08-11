"""Capability execution contracts shared by local and future external adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import CapabilityOffer
from .selection import OfferSelectionDecision

CAPABILITY_EXECUTION_SCHEMA_VERSION = 1


class CapabilityExecutionError(RuntimeError):
    pass


class InvalidCapabilityInput(CapabilityExecutionError):
    pass


class UnsupportedCapabilityExecution(CapabilityExecutionError):
    pass


class CapabilityToolUnavailable(CapabilityExecutionError):
    pass


class CapabilityToolFailed(CapabilityExecutionError):
    pass


@dataclass(frozen=True)
class CapabilityExecutionResult:
    project_id: str
    capability_id: str
    offer_id: str
    adapter_id: str
    output: dict[str, Any]
    artifact: dict[str, Any] | None = None
    schema_version: int = CAPABILITY_EXECUTION_SCHEMA_VERSION

    @classmethod
    def from_offer(
        cls,
        *,
        project_id: str,
        offer: CapabilityOffer,
        output: dict[str, Any],
        artifact: dict[str, Any] | None = None,
    ) -> "CapabilityExecutionResult":
        return cls(
            project_id=project_id,
            capability_id=offer.capability_id,
            offer_id=offer.offer_id,
            adapter_id=offer.adapter_id,
            output=dict(output),
            artifact=None if artifact is None else dict(artifact),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "project_id": self.project_id,
            "capability_id": self.capability_id,
            "offer_id": self.offer_id,
            "adapter_id": self.adapter_id,
            "output": dict(self.output),
            "artifact": None if self.artifact is None else dict(self.artifact),
        }


@dataclass(frozen=True)
class CapabilityExecutionEnvelope:
    selection: OfferSelectionDecision
    result: CapabilityExecutionResult

    def to_dict(self) -> dict[str, Any]:
        return {
            "selection": self.selection.to_dict(),
            "result": self.result.to_dict(),
        }
