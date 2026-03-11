import asyncio
import os
import time
from src.ui_controller.live_streamer import GeminiLiveStreamer

async def run_multimodal_test():
    from microgravity.config.loader import load_config
    api_key = load_config().providers.gemini.api_key
    if not api_key:
         print("GEMINI_API_KEY not found in config.json")
         return
         
    streamer = GeminiLiveStreamer(api_key=api_key)
    
    # 1. Start session in background thread/loop via our streamer's logic
    # But for a simple test, we run it directly here
    
    print("[Test] Starting Gemini Multimodal Live Session...")
    print("[Test] Modalities: AUDIO, VIDEO (Screen), TEXT")
    
    system_instr = (
        "You are a multimodal AI assistant with access to the user's screen and microphone. "
        "Please verbally greet the user and describe what you see on their screen right now. "
        "Wait for them to speak and respond naturally."
    )
    
    # Run the streamer and the video loop concurrently
    async def run_logic():
        # Start the video stream loop
        video_task = asyncio.create_task(streamer.stream_screen_loop(fps=1.0))
        
        # Start the session
        session_task = asyncio.create_task(streamer.start_session(system_instruction=system_instr))
        
        await asyncio.sleep(5)
        print("[Test] Triggering a Magnified Closeup on the center of the screen (zoom 2x)...")
        streamer.set_roi(960, 540, zoom_factor=2.0)
        
        await asyncio.sleep(10)
        print("[Test] Resetting ROI to full screen...")
        streamer.reset_roi()
        
        await session_task
        video_task.cancel()

    try:
        await run_logic()
    except KeyboardInterrupt:
        print("[Test] Interrupted.")
    except Exception as e:
        print(f"[Test] Error: {e}")
    finally:
        await streamer.disconnect()

if __name__ == "__main__":
    # We need to make sure src is in path or run from root
    import sys
    sys.path.append(os.getcwd())
    asyncio.run(run_multimodal_test())
