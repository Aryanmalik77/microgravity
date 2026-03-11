import asyncio
import time
from typing import Dict, Any, List, Optional
from loguru import logger

class AttentionMode:
    FOCUSED = "FOCUSED"   # Intensive VLM/State extraction
    DIFFUSED = "DIFFUSED" # Low-resource background monitoring

class Observatory:
    """
    The sensory hub for the Agentic OS.
    Aggregates data from VisionEngine, ScreenObserver, and Cognition
    to provide a unified 'Observation' to the Planner.
    """
    def __init__(self, vision_engine: Any, screen_observer: Any, cognition_monitor: Any):
        self.vision = vision_engine
        self.screen = screen_observer
        self.cognition = cognition_monitor
        self.mode = AttentionMode.DIFFUSED
        self.last_observation: Optional[Dict[str, Any]] = None

    def set_attention_mode(self, mode: str):
        if mode == self.mode:
            return
        
        logger.info(f"[Observatory] Transitioning attention mode: {self.mode} -> {mode}")
        self.mode = mode
        
        if mode == AttentionMode.DIFFUSED:
            self.cognition.start()
        else:
            self.cognition.stop()

    async def get_observation(self, task_context: Optional[str] = None) -> Dict[str, Any]:
        """
        Takes a sensory snapshot based on the current attention mode.
        """
        logger.debug(f"[Observatory] Capture Observation (Mode: {self.mode})")
        
        # 1. Capture basic screen state
        screenshot_path = self.screen.capture(filename="observatory_snap.png")
        
        observation = {
            "timestamp": time.time(),
            "mode": self.mode,
            "screenshot_path": screenshot_path,
            "anomalies": self.cognition.report_status()
        }

        # 2. If Focused, perform intensive VLM analysis
        if self.mode == AttentionMode.FOCUSED:
            logger.info("[Observatory] Performing Focused State Analysis...")
            state_desc = await self.vision.get_ui_state(screenshot_path)
            observation["state_description"] = state_desc
            
            # Optional: Add environmental context (active window etc.)
            # observation["environmental_context"] = self.screen.get_environment_info()
        else:
            observation["state_description"] = "Background Monitoring Active."

        self.last_observation = observation
        return observation

    def get_latest_anomalies(self) -> List[Dict[str, Any]]:
        return self.cognition.anomalies_detected
