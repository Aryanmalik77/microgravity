from google import genai
import os

from microgravity.config.loader import load_config
config = load_config()
api_key = config.providers.gemini.api_key
client = genai.Client(api_key=api_key)

with open("available_bidi_models.txt", "w") as f:
    for model in client.models.list():
        methods = getattr(model, 'supported_generation_methods', [])
        if methods and any('bidi' in m.lower() for m in methods):
            f.write(f"{model.name} : {methods}\n")
print("Done writing to available_bidi_models.txt")
