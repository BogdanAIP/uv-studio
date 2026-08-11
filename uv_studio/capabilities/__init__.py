"""UV Studio semantic capabilities and adapter offers."""

from .builtin import ADAPTERS, CAPABILITIES, build_builtin_capability_registry
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
)

__all__ = [
    "ADAPTERS",
    "CAPABILITIES",
    "CAPABILITY_SCHEMA_VERSION",
    "AdapterDefinition",
    "AdapterKind",
    "CapabilityDefinition",
    "CapabilityOffer",
    "CapabilityRegistry",
    "CapabilityRegistryError",
    "CapabilityValidationError",
    "CostClass",
    "DuplicateAdapter",
    "DuplicateCapability",
    "DuplicateOffer",
    "LocalityClass",
    "MediaKind",
    "OfferAvailability",
    "OperationKind",
    "UnknownAdapter",
    "UnknownCapability",
    "build_builtin_capability_registry",
]
