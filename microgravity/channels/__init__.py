"""Chat channels module with plugin architecture."""

from microgravity.channels.base import BaseChannel
from microgravity.channels.manager import ChannelManager

__all__ = ["BaseChannel", "ChannelManager"]
