import os
import http.client
import json

def verify_key(api_key):
    print(f"Testing API Key: {api_key[:10]}...")
    conn = http.client.HTTPSConnection("generativelanguage.googleapis.com")
    headers = {'Content-Type': 'application/json'}
    # Just list models to check key validity
    url = f"/v1beta/models?key={api_key}"
    
    conn.request("GET", url, headers=headers)
    response = conn.getresponse()
    data = response.read().decode('utf-8')
    
    print(f"Status: {response.status}")
    try:
        parsed = json.loads(data)
        if response.status == 200:
            print("Successfully retrieved models. Key is VALID.")
            if 'models' in parsed:
                print(f"Found {len(parsed['models'])} models.")
        else:
            print("Error response received:")
            print(json.dumps(parsed, indent=2))
    except Exception as e:
        print(f"Failed to parse response: {e}")
        print(data)

if __name__ == "__main__":
    import sys
    from pathlib import Path
    # Ensure project root is in path
    sys.path.append(str(Path.cwd()))
    from microgravity.config.loader import load_config
    
    config = load_config()
    api_key = config.providers.gemini.api_key
    
    if api_key:
        verify_key(api_key)
    else:
        print("Error: Gemini API key not found in config.")
