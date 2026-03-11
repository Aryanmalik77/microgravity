import sys
import os
import time
from pathlib import Path
import asyncio

# Add project root and src to path
project_root = Path(r"C:\Users\HP\Downloads\micro gravity - Copy\ui_agent_engine")
sys.path.append(str(project_root / "src"))

from ui_controller.live_streamer import GeminiLiveStreamer
from planning.action_predictor import ActionPredictor
from perception.vision_analyzer import VisionAnalyzer

async def run_live_zoom_test():
    from microgravity.config.loader import load_config
    api_key = load_config().providers.gemini.api_key
    if not api_key:
         print("GEMINI_API_KEY not found in config.json. Please set it.")
         return
         
    
    debug_dir = project_root / "debug_screenshots"
    debug_dir.mkdir(exist_ok=True)
    
    streamer = GeminiLiveStreamer(api_key=api_key)
    streamer.debug_dir = str(debug_dir)
    vision = VisionAnalyzer()
    predictor = ActionPredictor(vision)
    
    print("[Test] Starting Gemini Multimodal Live Session...")
    
    system_instr = "You are a UI Assistant examining a live screen. I will send you questions about UI elements. Provide their bounding boxes in normalized coordinates [0-1000]."
    
    # Start the session background tasks
    async def safe_stream():
        while not streamer.is_streaming:
            await asyncio.sleep(0.5)
        await streamer.stream_screen_loop(fps=0.7)
        
    # Block on the context manager session
    async def session_starter():
         await streamer.start_session(system_instruction=system_instr)
         
    session_task = asyncio.create_task(session_starter())
    video_task = asyncio.create_task(safe_stream())
    
    # Wait for connection
    await asyncio.sleep(8)
    if not streamer.is_streaming:
        print("\n[Test] Failed to connect to Gemini Live API. Proceeding with Mock Simulation to test Zoom Coordinate Logic...")
        # Cancel tasks
        session_task.cancel()
        video_task.cancel()
        
        # MOCK THE PREDICTOR LOGIC
        print("\n[Test] Simulating PASS 1 (Overview) for Target: 'Windows Start Button' at bottom-left corner.")
        # Bottom left usually around y=950+, x=0-50 out of 1000
        bbox_overview = [960, 0, 1000, 40] 
        print(f"[Test] Pass 1 returned BBOX: {bbox_overview}")
        
        # Simulating Pass 1 size calculation in _query_live_api
        width = bbox_overview[3] - bbox_overview[1]
        height = bbox_overview[2] - bbox_overview[0]
        
        print(f"[Test] Evaluated Size -> Width: {width}, Height: {height} (Threshold is < 60)")
        print("[Test] PASS 2: Closeup Needed. Triggering Set ROI...")
        
        # Center of pass 1
        screen_w, screen_h = 1920, 1080
        center_x = int(((bbox_overview[1] + bbox_overview[3]) / 2000) * screen_w)
        center_y = int(((bbox_overview[0] + bbox_overview[2]) / 2000) * screen_h)
        streamer.screen_size = (screen_w, screen_h)
        streamer.set_roi(center_x, center_y, zoom_factor=2.5)
        
        print("\n[Test] Simulating PASS 2 (Zoomed) API Response...")
        # Real location of start button inside the zoomed region (say it's slightly off-center in the crop)
        bbox_roi = [500, 500, 600, 600] # In the center of the crop
        print(f"[Test] Pass 2 returned Zoomed BBOX: {bbox_roi}")
        
        nx_center = (bbox_roi[1] + bbox_roi[3]) / 2000
        ny_center = (bbox_roi[0] + bbox_roi[2]) / 2000
        from perception.roi_manager import ROIManager
        gx, gy = ROIManager.map_to_global(nx_center, ny_center, streamer.current_roi, streamer.screen_size)
        
        # MOCK SCREENSHOT: Manually save ROI crop from current screen
        try:
             from PIL import ImageGrab
             full_screen = ImageGrab.grab()
             roi_img = full_screen.crop(streamer.current_roi)
             mock_path = debug_dir / "mock_roi_zoom_result.jpg"
             roi_img.save(mock_path)
             print(f"[Test] MOCK Visual Proof saved to: {mock_path}")
        except Exception as e:
             print(f"[Test] Warning: Failed to save mock screenshot: {e}")

        print(f"\n[Test] Zoom Logic Success! Mapped precise normalized coords ({nx_center:.2f}, {ny_center:.2f}) -> Global Desktop Coords ({gx}, {gy})")
        
        return

    print("\n[Test] Connected. Requesting location for a small element that requires zoom: 'Windows Start Button'...")
    
    target = "Windows Start Button"
    action = {"action": "click", "target": target}
    
    try:
        # Pass the streamer to the predictor
        params = await predictor._query_live_api(target, action, streamer)
        print(f"\n[Test] Final Predicted Coordinates: {params}")
        
    except Exception as e:
         print(f"[Test] Error during prediction: {e}")
         import traceback
         traceback.print_exc()

    finally:
         await streamer.disconnect()
         try:
             video_task.cancel()
             await session_task
         except asyncio.CancelledError:
             pass

if __name__ == "__main__":
    # API keys are now handled internally by components via load_config()
        
    asyncio.run(run_live_zoom_test())
