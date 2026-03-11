import asyncio
import os
from google import genai

async def test_connection():
    from microgravity.config.loader import load_config
    config = load_config()
    api_key = config.providers.gemini.api_key
    client = genai.Client(api_key=api_key)
    
    models_to_test = ["gemini-2.0-flash-exp", "gemini-2.0-flash", "models/gemini-2.0-flash-exp"]
    
    for model in models_to_test:
        print(f"\n--- Testing Model: {model} ---")
        try:
            async with client.aio.live.connect(model=model, config={"response_modalities": ["AUDIO"]}) as session:
                print(f"SUCCESS with {model}")
                return
        except Exception as e:
            print(f"FAILED with {model}: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
