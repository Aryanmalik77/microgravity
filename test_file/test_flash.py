import asyncio
from google import genai
import os

async def test_flash():
    from microgravity.config.loader import load_config
    import sys
    import os
    # Ensure project root is in path
    sys.path.append(os.getcwd())
    
    config = load_config()
    api_key = config.providers.gemini.api_key
    if not api_key:
        print("ERROR: Gemini API key not found in config.")
        return

    client = genai.Client(api_key=api_key, http_options={'api_version': 'v1alpha'})
    
    models_to_test = ["gemini-2.0-flash-exp", "gemini-2.0-flash"]
    for model_name in models_to_test:
        try:
            print(f"Testing {model_name}...")
            async with client.aio.live.connect(model=model_name) as session:
                print(f"SUCCESS {model_name}")
        except Exception as e:
            print(f"ERROR for {model_name}: {repr(e)}")

if __name__ == "__main__":
    asyncio.run(test_flash())
