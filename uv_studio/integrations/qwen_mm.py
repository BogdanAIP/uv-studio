"""Pinned optional Qwen-MM-Plugins MCP profile/binding pack.

This module contains only trusted static profile templates and explicit semantic
bindings. It does not install Qwen-MM, invoke tools, or persist secret values.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Any

from uv_studio.capabilities import CostClass, LocalityClass
from uv_studio.mcp.models import (
    MCPConfiguration,
    MCPProfile,
    MCPProjectFileInput,
    MCPToolBinding,
)
from uv_studio.mcp.store import MCPConfigStore

QWEN_MM_REPOSITORY = "QwenLM/Qwen-MM-Plugins"
QWEN_MM_UPSTREAM_SHA = "7dfc08b7de8e621fc28bf9814e3d41a59b4595ae"
QWEN_MM_LICENSE = "Apache-2.0"
QWEN_MM_VERIFIED_DATE = "2026-08-11"
QWEN_MM_WINDOWS_SUPPORT = "wsl2_only"


class QwenMMPackError(RuntimeError):
    pass


class UnknownQwenMMPack(QwenMMPackError):
    pass


class QwenMMPlatformUnsupported(QwenMMPackError):
    pass


def _source_requirement(extra: str) -> str:
    return (
        f"qwen-mm-plugins[{extra}] @ "
        f"git+https://github.com/{QWEN_MM_REPOSITORY}.git@{QWEN_MM_UPSTREAM_SHA}"
    )


def _profile(
    *,
    profile_id: str,
    title: str,
    extra: str,
    entrypoint: str,
    requires_dashscope: bool,
) -> MCPProfile:
    return MCPProfile(
        profile_id=profile_id,
        title=title,
        command="uvx",
        args=("--from", _source_requirement(extra), entrypoint),
        env_refs=(("DASHSCOPE_API_KEY", "DASHSCOPE_API_KEY"),)
        if requires_dashscope
        else (),
        startup_timeout_sec=120,
        discovery_timeout_sec=30,
    )


def _binding(
    binding_id: str,
    profile_id: str,
    tool_name: str,
    capability_id: str,
    title: str,
    locality: LocalityClass,
    cost_class: CostClass,
    *,
    asynchronous: bool,
    features: tuple[str, ...] = (),
    project_file_inputs: tuple[MCPProjectFileInput, ...] = (),
) -> MCPToolBinding:
    return MCPToolBinding(
        binding_id=binding_id,
        profile_id=profile_id,
        tool_name=tool_name,
        capability_id=capability_id,
        title=title,
        locality=locality,
        cost_class=cost_class,
        asynchronous=asynchronous,
        features=features,
        project_file_inputs=project_file_inputs,
    )


@dataclass(frozen=True)
class QwenMMPackDefinition:
    pack_id: str
    title: str
    description: str
    profile: MCPProfile
    bindings: tuple[MCPToolBinding, ...]
    expected_tools: tuple[str, ...]
    intentionally_unbound_tools: tuple[str, ...]
    system_requirements: tuple[str, ...]
    cloud_backed: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "pack_id": self.pack_id,
            "title": self.title,
            "description": self.description,
            "upstream": {
                "repository": QWEN_MM_REPOSITORY,
                "commit": QWEN_MM_UPSTREAM_SHA,
                "license": QWEN_MM_LICENSE,
                "verified_date": QWEN_MM_VERIFIED_DATE,
            },
            "platform": {
                "native_windows_validated": False,
                "windows_support": QWEN_MM_WINDOWS_SUPPORT,
                "note": (
                    "Current upstream documents WSL2 as the only supported Windows environment; "
                    "native Windows has not been validated."
                ),
            },
            "profile": self.profile.to_dict(),
            "bindings": [binding.to_dict() for binding in self.bindings],
            "expected_tools": list(self.expected_tools),
            "intentionally_unbound_tools": list(self.intentionally_unbound_tools),
            "system_requirements": list(self.system_requirements),
            "cloud_backed": self.cloud_backed,
            "tool_execution_enabled": True,
            "execution_policy": {
                "mode": "generic_mcp_after_discovery_and_authorization",
                "automatic": False,
                "requires_ready_discovery": True,
                "authorization_enforced": True,
            },
        }


CORE_PROFILE_ID = "qwen-mm-core"
API_PROFILE_ID = "qwen-mm-api"
VIDEO_EDIT_PROFILE_ID = "qwen-mm-video-edit"

CORE_PACK = QwenMMPackDefinition(
    pack_id="core",
    title="Qwen-MM Core",
    description="Локальные операции чтения/визуализации медиа; без облачного API-ключа.",
    profile=_profile(
        profile_id=CORE_PROFILE_ID,
        title="Qwen-MM Core",
        extra="core",
        entrypoint="qwen-mm-plugins-core",
        requires_dashscope=False,
    ),
    bindings=(
        _binding(
            "qwen-mm-core.media-info",
            CORE_PROFILE_ID,
            "media_info",
            "media.probe",
            "Qwen-MM local media metadata",
            LocalityClass.LOCAL,
            CostClass.FREE,
            asynchronous=False,
            features=("media.metadata",),
            project_file_inputs=(
                MCPProjectFileInput(
                    argument_name="path",
                    allowed_roots=("sources", "assets", "artifacts", "exports"),
                ),
            ),
        ),
    ),
    expected_tools=(
        "read_image",
        "read_video",
        "media_info",
        "visualize",
        "crop",
        "draw_bbox",
        "save_view",
    ),
    intentionally_unbound_tools=(
        "read_image",
        "read_video",
        "visualize",
        "crop",
        "draw_bbox",
        "save_view",
    ),
    system_requirements=("uv", "ffmpeg"),
    cloud_backed=False,
)

API_PACK = QwenMMPackDefinition(
    pack_id="api",
    title="Qwen-MM API",
    description="Облачное мультимодальное понимание/ASR через текущий DashScope-backed API plugin.",
    profile=_profile(
        profile_id=API_PROFILE_ID,
        title="Qwen-MM API",
        extra="api",
        entrypoint="qwen-mm-plugins-api",
        requires_dashscope=True,
    ),
    bindings=(
        _binding(
            "qwen-mm-api.vision-chat",
            API_PROFILE_ID,
            "vision_chat",
            "media.understand",
            "Qwen vision chat",
            LocalityClass.REMOTE,
            CostClass.POTENTIALLY_PAID,
            asynchronous=True,
            features=("vision.multimodal",),
        ),
        _binding(
            "qwen-mm-api.ocr",
            API_PROFILE_ID,
            "ocr",
            "media.understand",
            "Qwen OCR",
            LocalityClass.REMOTE,
            CostClass.POTENTIALLY_PAID,
            asynchronous=True,
            features=("vision.ocr",),
        ),
        _binding(
            "qwen-mm-api.grounding",
            API_PROFILE_ID,
            "grounding",
            "media.understand",
            "Qwen visual grounding",
            LocalityClass.REMOTE,
            CostClass.POTENTIALLY_PAID,
            asynchronous=True,
            features=("vision.grounding",),
        ),
        _binding(
            "qwen-mm-api.transcribe-audio",
            API_PROFILE_ID,
            "transcribe_audio",
            "speech.transcribe",
            "Qwen ASR transcription",
            LocalityClass.REMOTE,
            CostClass.POTENTIALLY_PAID,
            asynchronous=True,
            features=("speech.asr",),
        ),
        _binding(
            "qwen-mm-api.omni-av-caption",
            API_PROFILE_ID,
            "omni_av_caption",
            "media.understand",
            "Qwen Omni A/V captioning",
            LocalityClass.REMOTE,
            CostClass.POTENTIALLY_PAID,
            asynchronous=True,
            features=("media.timestamped_caption",),
        ),
        _binding(
            "qwen-mm-api.omni-asr",
            API_PROFILE_ID,
            "omni_asr",
            "speech.transcribe",
            "Qwen Omni ASR",
            LocalityClass.REMOTE,
            CostClass.POTENTIALLY_PAID,
            asynchronous=True,
            features=("speech.asr",),
        ),
        _binding(
            "qwen-mm-api.omni-asr-timestamped",
            API_PROFILE_ID,
            "omni_asr_timestamped",
            "speech.transcribe",
            "Qwen Omni timestamped ASR",
            LocalityClass.REMOTE,
            CostClass.POTENTIALLY_PAID,
            asynchronous=True,
            features=("speech.asr", "speech.timestamps"),
        ),
        _binding(
            "qwen-mm-api.omni-multi-speaker-asr",
            API_PROFILE_ID,
            "omni_multi_speaker_asr",
            "speech.transcribe",
            "Qwen Omni multi-speaker ASR",
            LocalityClass.REMOTE,
            CostClass.POTENTIALLY_PAID,
            asynchronous=True,
            features=("speech.asr", "speech.diarization"),
        ),
        _binding(
            "qwen-mm-api.omni-av-grounding",
            API_PROFILE_ID,
            "omni_av_grounding",
            "media.understand",
            "Qwen Omni temporal grounding",
            LocalityClass.REMOTE,
            CostClass.POTENTIALLY_PAID,
            asynchronous=True,
            features=("media.temporal_grounding",),
        ),
        _binding(
            "qwen-mm-api.omni-av-counting",
            API_PROFILE_ID,
            "omni_av_counting",
            "media.understand",
            "Qwen Omni event counting",
            LocalityClass.REMOTE,
            CostClass.POTENTIALLY_PAID,
            asynchronous=True,
            features=("media.event_counting",),
        ),
        _binding(
            "qwen-mm-api.omni-music-caption",
            API_PROFILE_ID,
            "omni_music_caption",
            "media.understand",
            "Qwen Omni music captioning",
            LocalityClass.REMOTE,
            CostClass.POTENTIALLY_PAID,
            asynchronous=True,
            features=("audio.music_analysis",),
        ),
    ),
    expected_tools=(
        "vision_chat",
        "ocr",
        "grounding",
        "omni_av_caption",
        "omni_asr",
        "omni_asr_timestamped",
        "omni_multi_speaker_asr",
        "omni_av_grounding",
        "omni_av_counting",
        "omni_music_caption",
        "transcribe_audio",
        "segmentation",
    ),
    intentionally_unbound_tools=("segmentation",),
    system_requirements=("uv", "DASHSCOPE_API_KEY"),
    cloud_backed=True,
)

VIDEO_EDIT_PACK = QwenMMPackDefinition(
    pack_id="video-edit",
    title="Qwen-MM Video Edit Generation",
    description="Облачные image/TTS/video generation tools; локальная ffmpeg-методика остаётся отдельной.",
    profile=_profile(
        profile_id=VIDEO_EDIT_PROFILE_ID,
        title="Qwen-MM Video Edit",
        extra="video-edit",
        entrypoint="qwen-mm-plugins-video-edit",
        requires_dashscope=True,
    ),
    bindings=(
        _binding(
            "qwen-mm-video-edit.qwen-image",
            VIDEO_EDIT_PROFILE_ID,
            "qwen_image",
            "image.generate",
            "Qwen image generation",
            LocalityClass.REMOTE,
            CostClass.POTENTIALLY_PAID,
            asynchronous=True,
            features=("image.text_to_image",),
        ),
        _binding(
            "qwen-mm-video-edit.qwen-tts",
            VIDEO_EDIT_PROFILE_ID,
            "qwen_tts",
            "speech.synthesize",
            "Qwen TTS",
            LocalityClass.REMOTE,
            CostClass.POTENTIALLY_PAID,
            asynchronous=True,
            features=("speech.tts",),
        ),
        _binding(
            "qwen-mm-video-edit.wan-t2v",
            VIDEO_EDIT_PROFILE_ID,
            "wan_t2v",
            "video.generate",
            "Wan text-to-video",
            LocalityClass.REMOTE,
            CostClass.POTENTIALLY_PAID,
            asynchronous=True,
            features=("video.text_to_video",),
        ),
        _binding(
            "qwen-mm-video-edit.wan-s2v",
            VIDEO_EDIT_PROFILE_ID,
            "wan_s2v",
            "video.digital_human",
            "Wan supplied-audio digital human",
            LocalityClass.REMOTE,
            CostClass.POTENTIALLY_PAID,
            asynchronous=True,
            features=("video.lip_sync", "video.supplied_audio"),
        ),
    ),
    expected_tools=("qwen_image", "qwen_tts", "wan_s2v", "wan_t2v", "happyhorse"),
    intentionally_unbound_tools=("happyhorse",),
    system_requirements=("uv", "DASHSCOPE_API_KEY"),
    cloud_backed=True,
)

QWEN_MM_PACKS = (CORE_PACK, API_PACK, VIDEO_EDIT_PACK)
_PACKS_BY_ID = {pack.pack_id: pack for pack in QWEN_MM_PACKS}


def list_qwen_mm_packs() -> tuple[QwenMMPackDefinition, ...]:
    return QWEN_MM_PACKS


def get_qwen_mm_pack(pack_id: str) -> QwenMMPackDefinition:
    try:
        return _PACKS_BY_ID[pack_id]
    except KeyError as exc:
        raise UnknownQwenMMPack(pack_id) from exc


def native_process_supported(platform: str | None = None) -> bool:
    current = sys.platform if platform is None else platform
    return not current.startswith("win")


def configure_qwen_mm_pack(
    store: MCPConfigStore,
    pack_id: str,
    *,
    platform: str | None = None,
) -> MCPConfiguration:
    """Persist one known pinned profile and its bindings without secret values."""

    pack = get_qwen_mm_pack(pack_id)
    if not native_process_supported(platform):
        raise QwenMMPlatformUnsupported(
            "Current Qwen-MM upstream supports Windows through WSL2 only; "
            "native Windows profile configuration is intentionally blocked."
        )

    current = store.load()
    profiles = tuple(
        profile for profile in current.profiles if profile.profile_id != pack.profile.profile_id
    ) + (pack.profile,)
    bindings = tuple(
        binding
        for binding in current.bindings
        if binding.profile_id != pack.profile.profile_id
    ) + pack.bindings
    updated = MCPConfiguration(profiles=profiles, bindings=bindings)
    return store.save(updated)
