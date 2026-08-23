"""UV Studio capability adapters and adapter metadata translators."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..execution import CapabilityExecutionResult
from ..models import CapabilityOffer
from .artifact_preview import create_artifact_preview
from .audio_loudness import measure_prepared_audio_loudness
from .audio_visualizer import render_audio_visualizer
from .dubbing_render import render_dubbing_state
from .edit_render import render_edit_state
from .mcp import MCPBindingOfferAdapter
from .musetalk import MuseTalkAdapter
from .music_video_render import render_music_video_state
from .narrated_render import render_narrated_workspace
from .native_videoclaw import NativeVideoClawAdapter
from .photo_slideshow import compose_photo_slideshow
from .range_reinsertion import LocalFFmpegRangeAdapter
from .whisper_cpp import WhisperCppAdapter


class LocalFFmpegAdapter:
    """Stable package-level facade over bounded local FFmpeg operation handlers.

    The historical range adapter remains the delegate for probe/extract/assemble and
    exact single-range reinsertion. New project render/preview/analysis operations are
    explicit handlers, not another inheritance layer.
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
        if offer.capability_id == "video.render_dubbing":
            self._delegate._validate_offer(offer)
            return render_dubbing_state(
                self._delegate,
                project_id=project_id,
                offer=offer,
                payload=payload,
            )
        if offer.capability_id == "video.render_music_video":
            self._delegate._validate_offer(offer)
            return render_music_video_state(
                self._delegate,
                project_id=project_id,
                offer=offer,
                payload=payload,
            )
        if offer.capability_id == "video.render_narrated":
            self._delegate._validate_offer(offer)
            return render_narrated_workspace(
                self._delegate,
                project_id=project_id,
                offer=offer,
                payload=payload,
            )
        if offer.capability_id == "video.preview_artifact":
            self._delegate._validate_offer(offer)
            return create_artifact_preview(
                self._delegate,
                project_id=project_id,
                offer=offer,
                payload=payload,
            )
        if offer.capability_id == "audio.measure_loudness":
            self._delegate._validate_offer(offer)
            return measure_prepared_audio_loudness(
                self._delegate,
                project_id=project_id,
                offer=offer,
                payload=payload,
            )
        if offer.capability_id == "video.compose_photos":
            self._delegate._validate_offer(offer)
            return compose_photo_slideshow(
                self._delegate,
                project_id=project_id,
                offer=offer,
                payload=payload,
            )
        if offer.capability_id == "audio.visualize":
            self._delegate._validate_offer(offer)
            return render_audio_visualizer(
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


__all__ = [
    "LocalFFmpegAdapter",
    "MCPBindingOfferAdapter",
    "MuseTalkAdapter",
    "NativeVideoClawAdapter",
    "WhisperCppAdapter",
]
