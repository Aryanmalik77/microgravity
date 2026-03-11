import os
from google import genai
from loguru import logger

def test_static_models():
    from microgravity.config.loader import load_config
    import sys
    sys.path.append(os.getcwd())
    config = load_config()
    api_key = config.providers.gemini.api_key
    output_file = "model_results.txt"
    with open(output_file, "w") as f:
        f.write(f"API Key present: {api_key is not None}\n")
        if not api_key:
            f.write("ERROR: GEMINI_API_KEY is missing\n")
            return

        client_default = genai.Client(api_key=api_key)
        client_v1beta = genai.Client(api_key=api_key, http_options={'api_version': 'v1beta'})
        
        models_to_test = [
            "gemini-1.5-flash",
            "gemini-1.5-flash-latest",
            "gemini-2.0-flash-exp",
            "gemini-2.0-flash",
            "models/gemini-1.5-flash",
            "models/gemini-2.0-flash-exp"
        ]
        
        clients = [
            ("default", client_default),
            ("v1beta", client_v1beta)
        ]
        
        for client_name, client in clients:
            f.write(f"\n--- Testing with client: {client_name} ---\n")
            for model in models_to_test:
                try:
                    response = client.models.generate_content(
                        model=model,
                        contents="Say hello"
                    )
                    f.write(f"  [SUCCESS] {model}: {response.text[:20]}...\n")
                except Exception as e:
                    f.write(f"  [FAIL] {model}: {str(e)[:100]}\n")

if __name__ == "__main__":
    test_static_models()
