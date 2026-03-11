import asyncio
import os
import sys
import json
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock
from loguru import logger

# Ensure project root is in path
sys.path.append(os.getcwd())
# API keys are now handled internally by components via load_config()

print("[Diagnostic] Starting verification script imports...")
try:
    from src.memory.kernel import MemoryKernel
    from src.intelligence.perception.engine import VisionEngine
    from src.intelligence.perception.live_streamer import GeminiLiveStreamer
    print("[Diagnostic] Imports successful.")
except Exception as e:
    print(f"[Diagnostic] Import failed: {e}")
    sys.exit(1)

async def verify_closeup_storage():
    workspace = Path.cwd()
    storage_dir = workspace / "storage"
    # Ensure atlas exists
    atlas_path = storage_dir / "memory" / "atlas" / "ui_atlas.json"
    
    logger.info("[Verify] Initializing Memory and Vision...")
    memory = MemoryKernel(storage_dir)
    vision = VisionEngine(memory_kernel=memory)
    
    # Mock Live Streamer
    mock_streamer = MagicMock(spec=GeminiLiveStreamer)
    mock_streamer.is_streaming = True
    mock_streamer.screen_size = (1920, 1080)
    mock_streamer.current_roi = (500, 500, 1000, 1000) # Simulating a zoom ROI
    mock_streamer.send_prompt = AsyncMock()
    mock_streamer.send_frame_now = AsyncMock()
    
    vision.attach_live_streamer(mock_streamer)
    
    # Test target
    target = "test_button"
    logger.info(f"[Verify] Attempting to resolve '{target}' with zoom...")
    
    # Pass 2 behavior: When vision asks for JSON, we trigger the callback
    async def simulate_api_response():
        # wait a bit to simulate network
        await asyncio.sleep(0.5)
        # Call the callback that VisionEngine registered
        vision.live_streamer.on_response_callback({
            "bounding_box": [500, 500, 600, 600] # Normalized coords in ROI
        })

    # Trigger resolution
    # We need to run the API simulation in the background
    asyncio.create_task(simulate_api_response())
    
    result = await vision.resolve_target_with_zoom(target, hint_coords=[950, 50], needs_zoom=True)
    
    logger.info(f"[Verify] Resolution result: {result}")
    
    # Verify Global Coordination Mapping
    # ROI: (500, 500, 1000, 1000) -> width=500, height=500
    # Normalized [500, 500, 600, 600] -> center_nx=0.55, center_ny=0.55 
    # Actually ny = (500+600)/2000 = 0.55, nx = (500+600)/2000 = 0.55
    # Global X = 500 + 0.55 * 500 = 775
    # Global Y = 500 + 0.55 * 500 = 775
    
    expected_x = 775
    expected_y = 775
    
    if abs(result['x'] - expected_x) < 5 and abs(result['y'] - expected_y) < 5:
        logger.success("[Verify] Coordinate mapping SUCCESS.")
    else:
        logger.error(f"[Verify] Coordinate mapping FAILED. Expected ~({expected_x}, {expected_y}), got ({result['x']}, {result['y']})")

    # Verify Memory Persistence
    cached = memory.recall_element("Desktop", target)
    if cached:
        logger.success(f"[Verify] Element '{target}' FOUND in memory.")
        logger.info(f"[Verify] Cached Coords: {cached['coords']}")
    else:
        logger.error(f"[Verify] Element '{target}' NOT found in memory.")

    # Check the JSON file on disk
    with open(atlas_path, 'r') as f:
        atlas_data = json.load(f)
        if target.lower() in atlas_data["contexts"]["Desktop"]["elements"]:
            logger.success("[Verify] UI Atlas JSON updated on disk.")
        else:
            logger.error("[Verify] UI Atlas JSON NOT updated.")

if __name__ == "__main__":
    asyncio.run(verify_closeup_storage())
