import os, json, asyncio
from google import genai

config_path = r"c:\Users\HP\.nanobot\config.json"
with open(config_path, 'r') as f:
    config = json.load(f)
api_key = config.get("providers", {}).get("gemini", {}).get("apiKey")

out_path = r"c:\Users\HP\Downloads\micro gravity - Copy\ui_agent_engine\ws_results2.txt"
lines = []

# These are the EXACT model names from ListModels that have 'native-audio'
MODELS = [
    "gemini-2.5-flash-native-audio-latest",
    "gemini-2.5-flash-native-audio-preview-09-2025",
    "gemini-2.5-flash-native-audio-preview-12-2025",
    "gemini-2.5-flash-preview-tts",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-3-flash-preview",
]

async def test():
    for api_ver in ['v1alpha', 'v1beta']:
        c = genai.Client(api_key=api_key, http_options={'api_version': api_ver})
        for m in MODELS:
            for modality in [["AUDIO"], ["TEXT"]]:
                try:
                    cfg = {"response_modalities": modality}
                    async with c.aio.live.connect(model=m, config=cfg) as sess:
                        lines.append(f"[OK] {api_ver}/{m} mod={modality} CONNECTED!")
                        return (m, api_ver, modality)
                except Exception as e:
                    lines.append(f"[X] {api_ver}/{m} mod={modality}: {str(e)[:120]}")
    return None

r = asyncio.run(test())
lines.append(f"\nFINAL: {r}")

with open(out_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
print(f"Done. Results in {out_path}")
