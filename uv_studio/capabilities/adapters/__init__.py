"""UV Studio capability adapters and adapter metadata translators."""

from .local_ffmpeg import LocalFFmpegAdapter
from .mcp import MCPBindingOfferAdapter

__all__ = ["LocalFFmpegAdapter", "MCPBindingOfferAdapter"]
