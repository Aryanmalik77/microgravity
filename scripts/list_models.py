import os
from google import genai
from loguru import logger

def list_models():
    from microgravity.config.loader import load_config
    api_key = load_config().providers.gemini.api_key
    if not api_key:
        print("GEMINI_API_KEY missing in config.json")
        return
    
    client = genai.Client(api_key=api_key)
    print("--- Available Models ---")
    try:
        for model in client.models.list():
            print(f"Name: {model.name}, Supported Methods: {model.supported_generation_methods}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_models()
