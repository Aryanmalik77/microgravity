import os
from google import genai

def list_models():
    from microgravity.config.loader import load_config
    import sys
    sys.path.append(os.getcwd())
    config = load_config()
    api_key = config.providers.gemini.api_key
    client = genai.Client(api_key=api_key)
    try:
        print(f"Listing models for key: {api_key[:5]}...")
        for model in client.models.list():
            print(f" - {model.name}")
    except Exception as e:
        print(f"FAILURE: {type(e).__name__}: {e}")

if __name__ == "__main__":
    list_models()
