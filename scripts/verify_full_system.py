import asyncio
import os
import sys
import json
from pathlib import Path
from loguru import logger

# Ensure project root is in path
sys.path.append(os.getcwd())
# API keys are now handled internally by components via load_config()

from src.memory.kernel import MemoryKernel
from src.intelligence.perception.engine import VisionEngine
from src.kernel.interceptor import SafetyInterceptor, PowerLevel
from src.intelligence.planner.evaluator import FeedbackEvaluator
from src.kernel.config_manager import AgentConfigManager

class MockLiveStreamer:
    def __init__(self):
        self.is_streaming = True
        self.screen_size = (1920, 1080)
        self.current_roi = (0, 0, 1920, 1080)
        self.on_response_callback = None
    
    def set_roi(self, cx, cy, zoom_factor=2.0):
        self.current_roi = (500, 500, 1000, 1000)
    
    def reset_roi(self):
        self.current_roi = (0, 0, 1920, 1080)

    def set_callback(self, cb):
        self.on_response_callback = cb
    
    async def send_frame_now(self):
        pass

    async def send_prompt(self, text: str):
        if "MAGNIFIED CLOSEUP" in text:
            # Trigger response in the background
            asyncio.create_task(self._simulate_response())

    async def _simulate_response(self):
        await asyncio.sleep(0.5)
        if self.on_response_callback:
            logger.info("[Mock] Triggering callback with bounding box.")
            self.on_response_callback({"bounding_box": [500, 500, 600, 600]})
        else:
            logger.error("[Mock] callback is still NONE!")

async def verify_full_system():
    workspace = Path.cwd()
    storage_dir = workspace / "storage"
    logger.info("--- Starting Full System Integration Verification ---")

    # 1. Initialize Components
    memory = MemoryKernel(storage_dir)
    vision = VisionEngine(memory_kernel=memory)
    interceptor = SafetyInterceptor()
    config_manager = AgentConfigManager()
    evaluator = FeedbackEvaluator(config_manager=config_manager)
    
    mock_streamer = MockLiveStreamer()
    vision.attach_live_streamer(mock_streamer)

    # 2. Test Safety Interceptor
    logger.info("[Test 1] Testing Safety Interceptor...")
    # 'run_terminal' should be blocked for OPERATOR
    dangerous_action = {"action": "run_terminal", "value": "rm -rf /"}
    is_safe, reason = interceptor.evaluate_action(dangerous_action, current_level=PowerLevel.OPERATOR)
    if not is_safe:
        logger.success(f"[Test 1] Interceptor blocked dangerous action: {reason}")
    else:
        logger.error("[Test 1] Interceptor FAILED to block 'run_terminal' at OPERATOR level.")

    # 3. Test Auto-Tune
    logger.info("[Test 2] Testing Auto-Tuning...")
    initial_zoom = config_manager.config["zoom_level"]
    for i in range(3):
        evaluator.log_action_result({"action": "click"}, success=False, error_message="Vision resolution failed")
    
    if config_manager.config["zoom_level"] > initial_zoom:
        logger.success(f"[Test 2] Auto-tune successfully increased zoom to {config_manager.config['zoom_level']}")
    else:
        logger.error(f"[Test 2] Auto-tune FAILED to increase zoom.")

    # 4. Test Zoom Resolution & Metadata Storage
    logger.info("[Test 3] Testing Zoom Resolution & Memory Storage...")
    target = "verify_button"
    result = await vision.resolve_target_with_zoom(target, hint_coords=[950, 50], needs_zoom=True)
    logger.info(f"[Test 3] Resolution Result: {result}")

    # Check Memory
    cached = memory.recall_element("Desktop", target)
    if cached and cached.get("type") == "zoom_resolved":
        logger.success(f"[Test 3] Metadata for '{target}' successfully stored in UI Atlas.")
    else:
        logger.error(f"[Test 3] Metadata for '{target}' NOT found in memory.")

    logger.info("--- Full System Verification Completed ---")

if __name__ == "__main__":
    asyncio.run(verify_full_system())
