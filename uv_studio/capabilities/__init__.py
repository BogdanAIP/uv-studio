"""UV Studio semantic capabilities, offer selection and execution contracts."""

from .builtin import ADAPTERS, CAPABILITIES, build_builtin_capability_registry as _build_builtin_registry
from .execution import (
    CAPABILITY_EXECUTION_SCHEMA_VERSION,
    CapabilityExecutionEnvelope,
    CapabilityExecutionError,
    CapabilityExecutionResult,
    CapabilityToolFailed,
    CapabilityToolUnavailable,
    InvalidCapabilityInput,
    UnsupportedCapabilityExecution,
)
from .models import (
    CAPABILITY_SCHEMA_VERSION,
    AdapterDefinition,
    AdapterKind,
    CapabilityDefinition,
    CapabilityOffer,
    CapabilityValidationError,
    CostClass,
    LocalityClass,
    MediaKind,
    OfferAvailability,
    OperationKind,
)
from .registry import (
    CapabilityRegistry,
    CapabilityRegistryError,
    DuplicateAdapter,
    DuplicateCapability,
    DuplicateOffer,
    UnknownAdapter,
    UnknownCapability,
    UnknownOffer,
)
from .selection import (
    NoEligibleOffer,
    OfferSelectionDecision,
    OfferSelectionError,
    OfferSelectionRequired,
    PinnedOfferRejected,
    SelectionPolicy,
    select_offer,
)


def build_builtin_capability_registry() -> CapabilityRegistry:
    registry = _build_builtin_registry()
    # Stage 4 editor projections stay explicit operation modules while callers
    # receive one complete semantic registry through this public function.
    from .adapters.artifact_preview import register_artifact_preview_capability
    from .adapters.edit_render import register_edit_render_capability

    register_edit_render_capability(registry)
    register_artifact_preview_capability(registry)
    return registry


__all__ = [
    "ADAPTERS",
    "CAPABILITIES",
    "CAPABILITY_EXECUTION_SCHEMA_VERSION",
    "CAPABILITY_SCHEMA_VERSION",
    "AdapterDefinition",
    "AdapterKind",
    "CapabilityDefinition",
    "CapabilityExecutionEnvelope",
    "CapabilityExecutionError",
    "CapabilityExecutionResult",
    "CapabilityOffer",
    "CapabilityRegistry",
    "CapabilityRegistryError",
    "CapabilityToolFailed",
    "CapabilityToolUnavailable",
    "CapabilityValidationError",
    "CostClass",
    "DuplicateAdapter",
    "DuplicateCapability",
    "DuplicateOffer",
    "InvalidCapabilityInput",
    "LocalityClass",
    "MediaKind",
    "NoEligibleOffer",
    "OfferAvailability",
    "OfferSelectionDecision",
    "OfferSelectionError",
    "OfferSelectionRequired",
    "OperationKind",
    "PinnedOfferRejected",
    "SelectionPolicy",
    "UnknownAdapter",
    "UnknownCapability",
    "UnknownOffer",
    "UnsupportedCapabilityExecution",
    "build_builtin_capability_registry",
    "select_offer",
]
