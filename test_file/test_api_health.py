import os
import asyncio
from google import genai
from google.genai.errors import APIError

async def check_api_health():
    from microgravity.config.loader import load_config
    api_key = load_config().providers.gemini.api_key

    if not api_key:
        print("ERROR: gemini.apiKey not found in config.json")
        return

    print("=" * 50)
    print("API HEALTH DIAGNOSTIC: Live Stream (bidiGenerateContent)")
    print("=" * 50)
    print(f"Using API Key: {api_key[:8]}...{api_key[-4:]}")

    client = genai.Client(api_key=api_key)
    models_to_test = [
        "gemini-2.0-flash-exp",
        "gemini-2.5-flash", 
        "gemini-2.0-flash",
        "gemini-2.0-flash-live-001"
    ]

    success = False
    for model in models_to_test:
        print(f"\n[Testing] Model: {model}")
        try:
            # Attempt to establish a Live WebSocket connection
            async with client.aio.live.connect(model=model) as session:
                print(f"  -> SUCCESS! Connected to {model}.")
                success = True
                break
        except APIError as e:
            print(f"  -> API ERROR: {e.code} - {e.message}")
        except Exception as e:
            print(f"  -> ERROR: {type(e).__name__}: {str(e)}")

    print("\n" + "=" * 50)
    if success:
        print("DIAGNOSIS: Live API is HEALTHY and working.")
    else:
        print("DIAGNOSIS: Live API is UNAVAILABLE.")
        print("REASON: Your current API key lacks permissions for 'bidiGenerateContent'.")
        print("        This is an account/key restriction from Google side.")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(check_api_health())
