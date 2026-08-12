"""UV Studio capability adapters and adapter metadata translators."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..execution import CapabilityExecutionResult
from ..models import CapabilityOffer
from .edit_render import render_edit_state
from .mcp import MCPBindingOfferAdapter
from .native_videoclaw import NativeVideoClawAdapter
from .range_reinsertion import LocalFFmpegRangeAdapter


class LocalFFmpegAdapter:
    """Stable package-level facade over bounded local FFmpeg operation handlers.

    The historical range adapter remains the delegate for probe/extract/assemble and
    exact single-range reinsertion. New edit-state rendering is an operation handler,
    not another inheritance layer.
    """

    adapter_id = LocalFFmpegRangeAdapter.adapter_id

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._delegate = LocalFFmpegRangeAdapter(*args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._delegate, name)

    def execute(
        self,
        *,
        project_id: str,
        offer: CapabilityOffer,
        payload: Mapping[str, Any],
    ) -> CapabilityExecutionResult:
        if offer.capability_id == "video.render_edits":
            self._delegate._validate_offer(offer)
            return render_edit_state(
                self._delegate,
                project_id=project_id,
                offer=offer,
                payload=payload,
            )
        return self._delegate.execute(
            project_id=project_id,
            offer=offer,
            payload=payload,
        )


__all__ = ["LocalFFmpegAdapter", "MCPBindingOfferAdapter", "NativeVideoClawAdapter"]
