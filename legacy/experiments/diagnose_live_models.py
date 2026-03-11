"""
Diagnose which models support bidiGenerateContent (Live API) with the current API key.
Tests multiple API versions and model names.
"""
import os, json, asyncio
from google import genai

# Load API key
config_path = r"c:\Users\HP\.nanobot\config.json"
with open(config_path, 'r') as f:
    config = json.load(f)
api_key = config.get("providers", {}).get("gemini", {}).get("apiKey")

print(f"API Key: {api_key[:8]}...{api_key[-4:]}")
print("=" * 60)

# Step 1: List all available models that support live/generateContent
print("\n[Step 1] Listing ALL available models...")
client = genai.Client(api_key=api_key)

try:
    models = client.models.list()
    live_capable = []
    for model in models:
        name = model.name
        methods = getattr(model, 'supported_generation_methods', []) or []
        if not methods:
            methods = []
        # Check display name and supported methods  
        method_list = list(methods) if methods else []
        has_bidi = any('bidi' in str(m).lower() for m in method_list)
        has_stream = any('stream' in str(m).lower() for m in method_list)
        
        if has_bidi:
            live_capable.append((name, method_list))
            print(f"  [LIVE] {name} -> {method_list}")
        elif has_stream:
            print(f"  [STREAM] {name} -> {method_list}")
    
    print(f"\n  Total models with bidiGenerateContent: {len(live_capable)}")
    
except Exception as e:
    print(f"  Error listing models: {e}")

# Step 2: Try connecting with different API versions
print("\n" + "=" * 60)
print("[Step 2] Testing Live WebSocket connections...")

api_versions = ['v1alpha', 'v1beta']
model_names = [
    'gemini-2.0-flash-live-001',
    'gemini-2.0-flash-exp', 
    'gemini-2.5-flash',
    'gemini-2.0-flash',
    'models/gemini-2.0-flash-live-001',
    'models/gemini-2.0-flash-exp',
]

async def test_connections():
    for api_ver in api_versions:
        print(f"\n--- API Version: {api_ver} ---")
        test_client = genai.Client(
            api_key=api_key,
            http_options={'api_version': api_ver}
        )
        
        for model_name in model_names:
            try:
                config = {"response_modalities": ["TEXT"]}
                async with test_client.aio.live.connect(model=model_name, config=config) as session:
                    print(f"  [SUCCESS] {model_name} connected!")
                    # Send a quick test
                    await session.send(input="Say hello", end_of_turn=True)
                    async for response in session.receive():
                        text = response.text if hasattr(response, 'text') else str(response)
                        print(f"    Response: {text[:80]}...")
                        break
                    return model_name, api_ver  # Return first working combo
            except Exception as e:
                err = str(e)[:80]
                print(f"  [FAIL] {model_name}: {err}")
    
    return None, None

working_model, working_api = asyncio.run(test_connections())

print("\n" + "=" * 60)
if working_model:
    print(f"[RESULT] WORKING COMBO FOUND!")
    print(f"  Model: {working_model}")
    print(f"  API Version: {working_api}")
else:
    print("[RESULT] No working Live API combination found.")
    print("  Your API key may not have Live API access enabled.")
print("=" * 60)
