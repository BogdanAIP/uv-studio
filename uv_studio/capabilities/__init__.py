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
    # Editor/media projections and optional local runtimes stay explicit modules
    # while callers receive one complete semantic registry through this function.
    from .adapters.argos_translate import register_argos_translate_adapter
    from .adapters.artifact_preview import register_artifact_preview_capability
    from .adapters.audio_loudness import register_audio_loudness_capability
    from .adapters.audio_visualizer import register_audio_visualizer_capability
    from .adapters.dubbing_render import register_dubbing_render_capability
    from .adapters.edit_render import register_edit_render_capability
    from .adapters.musetalk import register_musetalk_adapter
    from .adapters.music_video_render import register_music_video_render_capability
    from .adapters.photo_slideshow import register_photo_slideshow_capability
    from .adapters.webvtt_subtitles import register_webvtt_subtitle_adapter
    from .adapters.whisperx_alignment import register_whisperx_alignment_adapter
    from .music_analysis import register_music_analysis_capability

    register_edit_render_capability(registry)
    register_artifact_preview_capability(registry)
    register_audio_loudness_capability(registry)
    register_dubbing_render_capability(registry)
    register_music_video_render_capability(registry)
    register_photo_slideshow_capability(registry)
    register_audio_visualizer_capability(registry)
    register_music_analysis_capability(registry)
    register_musetalk_adapter(registry)
    register_argos_translate_adapter(registry)
    register_whisperx_alignment_adapter(registry)
    register_webvtt_subtitle_adapter(registry)
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
