import os
from google import genai

def list_official_models():
    from microgravity.config.loader import load_config
    import sys
    sys.path.append(os.getcwd())
    config = load_config()
    api_key = config.providers.gemini.api_key
    client = genai.Client(api_key=api_key)
    print("Listing available models from SDK:")
    try:
        for model in client.models.list():
            print(f"Name: {model.name}, DisplayName: {model.display_name}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_official_models()
