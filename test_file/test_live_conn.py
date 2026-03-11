import asyncio
import os
import sys
import traceback

# Gemini API key is now handled internally by GeminiLiveStreamer via load_config()

sys.path.append(r'C:\Users\HP\Downloads\micro gravity - Copy\ui_agent_engine\src')
from ui_controller.live_streamer import GeminiLiveStreamer

async def test():
    s = GeminiLiveStreamer()
    try:
        await s.start_session()
    except Exception as e:
        print("FATAL LIVE ERROR:")
        traceback.print_exc()

asyncio.run(test())
