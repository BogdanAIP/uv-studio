"""UV Studio capability adapters and adapter metadata translators."""

from .mcp import MCPBindingOfferAdapter
from .native_videoclaw import NativeVideoClawAdapter
from .range_reinsertion import LocalFFmpegRangeAdapter as LocalFFmpegAdapter

__all__ = ["LocalFFmpegAdapter", "MCPBindingOfferAdapter", "NativeVideoClawAdapter"]