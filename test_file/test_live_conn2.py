import asyncio
import os
import sys
import traceback
from google import genai
from google.genai import types

# Configuration
from microgravity.config.loader import load_config
config = load_config()
api_key = config.providers.gemini.api_key

client = genai.Client(api_key=api_key)

async def test_specific_model(model_name):
    print(f"\n--- Testing {model_name} ---")
    try:
        async with client.aio.live.connect(model=model_name, config={"response_modalities": ["AUDIO"]}) as session:
            print("SUCCESS! Session active.")
    except Exception as e:
        print(f"FAILED. Error details: {str(e)[:200]}")

async def run_all():
    models = ["gemini-2.0-flash-exp", "gemini-2.0-flash-live-001", "gemini-2.0-flash"]
    for m in models:
        await test_specific_model(m)

asyncio.run(run_all())
