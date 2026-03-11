import json
import urllib.request
import os
import traceback

from microgravity.config.loader import load_config
config = load_config()
api_key = config.providers.gemini.api_key

if not api_key:
    print("GEMINI_API_KEY not found in config.json.")
    sys.exit(1)

req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}")

try:
    res = urllib.request.urlopen(req)
    data = json.loads(res.read())
    print("Models supporting bidi/live:")
    for m in data.get('models', []):
        if 'bidi' in str(m).lower() or 'live' in str(m['name']).lower():
            print(f" - {m['name']}")
except Exception as e:
    print(f"Error checking models: {e}")
