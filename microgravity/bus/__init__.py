"""Message bus module for decoupled channel-agent communication."""

from microgravity.bus.events import InboundMessage, OutboundMessage
from microgravity.bus.queue import MessageBus

__all__ = ["MessageBus", "InboundMessage", "OutboundMessage"]
