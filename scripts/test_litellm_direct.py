import asyncio
import os
import sys

# Ensure nanobot is in Python path for local testing
sys.path.insert(0, r"c:\Users\HP\nanobot")

from microgravity.providers.litellm_provider import LiteLLMProvider

async def test_litellm():
    print("Testing LiteLLM Provider directly...")
    
    # Try with Gemini Flash specifically
    from microgravity.config.loader import load_config
    config = load_config()
    provider = LiteLLMProvider(
        api_key=config.providers.gemini.api_key,
        default_model="gemini/gemini-2.5-flash"
    )
    
    messages = [{"role": "user", "content": "Reply with 'Hello, LiteLLM Gemini is working!'"}]
    
    print("Sending request via acompletion...")
    response = await provider.chat(messages=messages, max_tokens=50)
    
    print("\n--- Response ---")
    print(response.content)
    print("--- Finish Reason ---")
    print(response.finish_reason)

if __name__ == "__main__":
    asyncio.run(test_litellm())
