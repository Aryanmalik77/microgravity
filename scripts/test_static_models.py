import os
from google import genai
from loguru import logger

def test_static_models():
    from microgravity.config.loader import load_config
    import sys
    sys.path.append(os.getcwd())
    config = load_config()
    api_key = config.providers.gemini.api_key
    client_default = genai.Client(api_key=api_key)
    client_v1beta = genai.Client(api_key=api_key, http_options={'api_version': 'v1beta'})
    
    models_to_test = [
        "gemini-1.5-flash",
        "gemini-1.5-flash-latest",
        "gemini-2.0-flash-exp",
        "gemini-2.0-flash",
    ]
    
    clients = [
        ("default", client_default),
        ("v1beta", client_v1beta)
    ]
    
    for client_name, client in clients:
        print(f"\n--- Testing with client: {client_name} ---")
        for model in models_to_test:
            try:
                response = client.models.generate_content(
                    model=model,
                    contents="Say hello"
                )
                print(f"  [SUCCESS] {model}: {response.text[:20]}...")
            except Exception as e:
                print(f"  [FAIL] {model}: {str(e)[:100]}")

if __name__ == "__main__":
    test_static_models()
