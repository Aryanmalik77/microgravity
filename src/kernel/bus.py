import asyncio
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from loguru import logger

class DurableEventBus:
    """
    A high-availability messaging system for the Agentic OS.
    Ensures that task statuses and inter-agent messages are persisted
    and recoverable across crashes.
    """
    def __init__(self, persistence_root: Path):
        self.log_dir = persistence_root / "bus_logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.inbound_queue = asyncio.Queue()
        self.outbound_queue = asyncio.Queue()
        self.subscribers: Dict[str, List[Callable]] = {}
        
        logger.info("[EventBus] Initialized at {}", self.log_dir)

    async def publish(self, topic: str, payload: Dict[str, Any]):
        """Publishes a message to a topic."""
        message = {
            "topic": topic,
            "payload": payload,
            "timestamp": time.time()
        }
        
        # Persist message
        log_file = self.log_dir / f"{int(message['timestamp'] * 1000)}.json"
        with open(log_file, "w") as f:
            json.dump(message, f)
            
        # Notify subscribers
        if topic in self.subscribers:
            for cb in self.subscribers[topic]:
                await cb(payload)
                
        logger.debug(f"[EventBus] Published to {topic}: {payload}")

    def subscribe(self, topic: str, callback: Callable):
        """Subscribes to a specific topic."""
        if topic not in self.subscribers:
            self.subscribers[topic] = []
        self.subscribers[topic].append(callback)
        logger.info(f"[EventBus] New subscription for topic: {topic}")
