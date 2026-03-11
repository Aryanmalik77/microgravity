import os, json, asyncio, sys
from google import genai

config_path = r"c:\Users\HP\.nanobot\config.json"
with open(config_path, 'r') as f:
    config = json.load(f)
api_key = config.get("providers", {}).get("gemini", {}).get("apiKey")

print(f"KEY: {api_key[:8]}...{api_key[-4:]}", flush=True)

# Step 1: Find models with bidiGenerateContent
client = genai.Client(api_key=api_key)
print("\n=== Models with bidiGenerateContent ===", flush=True)
bidi_models = []
for m in client.models.list():
    methods = list(getattr(m, 'supported_generation_methods', []) or [])
    if any('bidi' in str(x).lower() for x in methods):
        print(f"  FOUND: {m.name} -> {methods}", flush=True)
        bidi_models.append(m.name)

if not bidi_models:
    print("  NONE found. Checking if any model has 'live' in the name...", flush=True)
    for m in client.models.list():
        if 'live' in m.name.lower():
            print(f"  LIVE-named: {m.name}", flush=True)
            bidi_models.append(m.name)

print(f"\nTotal bidi-capable: {len(bidi_models)}", flush=True)

# Step 2: Try WebSocket connections
print("\n=== Testing WebSocket Connections ===", flush=True)
test_models = bidi_models + [
    'gemini-2.0-flash-live-001',
    'gemini-2.0-flash-exp', 
    'gemini-2.5-flash-preview-native-audio-dialog',
    'gemini-2.0-flash',
]
# Remove duplicates
test_models = list(dict.fromkeys(test_models))

async def try_connect():
    for api_ver in ['v1alpha', 'v1beta']:
        c = genai.Client(api_key=api_key, http_options={'api_version': api_ver})
        for model in test_models:
            try:
                cfg = {"response_modalities": ["TEXT"]}
                async with c.aio.live.connect(model=model, config=cfg) as sess:
                    print(f"  [OK] {api_ver}/{model} CONNECTED!", flush=True)
                    return model, api_ver
            except Exception as e:
                print(f"  [X] {api_ver}/{model}: {str(e)[:60]}", flush=True)
    return None, None

model, ver = asyncio.run(try_connect())
print(f"\nRESULT: model={model}, api_version={ver}", flush=True)
