"""UV Studio capability adapters and adapter metadata translators."""

from .local_ffmpeg import LocalFFmpegAdapter
from .mcp import MCPBindingOfferAdapter
from .native_videoclaw import NativeVideoClawAdapter

__all__ = ["LocalFFmpegAdapter", "MCPBindingOfferAdapter", "NativeVideoClawAdapter"]