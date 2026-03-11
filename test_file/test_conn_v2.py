import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), "Agentic", "agentic_swarm"))

import os
from google import genai

from microgravity.config.loader import load_config

def test_connectivity():
    # Use the key from the consolidated config
    config = load_config()
    api_key = config.providers.gemini.api_key
    if not api_key:
        print("FAILURE: Gemini API key not found in config.")
        return

    print(f"Testing connectivity with API Key: {api_key[:5]}...")
    
    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents="Say hello"
        )
        print(f"SUCCESS: {response.text}")
    except Exception as e:
        print(f"FAILURE: {type(e).__name__}: {e}")

if __name__ == "__main__":
    test_connectivity()
