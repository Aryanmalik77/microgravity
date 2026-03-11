import os
import httpx
import json

def list_models_direct():
    from microgravity.config.loader import load_config
    api_key = load_config().providers.gemini.api_key
    if not api_key:
        print("GEMINI_API_KEY missing in config.json")
        return
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        response = httpx.get(url)
        if response.status_code == 200:
            data = response.json()
            for model in data.get("models", []):
                print(f"Name: {model.get('name')}, Methods: {model.get('supportedGenerationMethods')}")
        else:
            print(f"Error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    list_models_direct()
