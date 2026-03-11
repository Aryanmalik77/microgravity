from google import genai
import os

from microgravity.config.loader import load_config
config = load_config()
api_key = config.providers.gemini.api_key
client = genai.Client(api_key=api_key)

with open("flash_methods.txt", "w") as f:
    try:
        model = client.models.get(model="gemini-2.0-flash")
        f.write(f"gemini-2.0-flash methods: {getattr(model, 'supported_generation_methods', [])}\n")
    except Exception as e:
        f.write(f"ERROR: {e}\n")
print("Done")
