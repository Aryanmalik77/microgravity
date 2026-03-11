import os
from google import genai

def test_connectivity():
    from microgravity.config.loader import load_config
    api_key = load_config().providers.gemini.api_key
    if not api_key:
        print("GEMINI_API_KEY not found in config.json.")
        return
    
    print(f"Testing connectivity with API Key from config: {api_key[:5]}...")
    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents="Say hello"
        )
        print(f"SUCCESS: {response.text}")
    except Exception as e:
        print(f"FAILURE: {e}")

if __name__ == "__main__":
    test_connectivity()
