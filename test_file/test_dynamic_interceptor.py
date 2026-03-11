import asyncio
from pathlib import Path
from microgravity.agent.loop import AgentLoop
from microgravity.bus.queue import MessageBus
from microgravity.providers.openai_provider import OpenAIProvider
import os

async def test_memory_trigger():
    workspace = Path("c:/Users/HP/nanobot/workspace")
    bus = MessageBus()
    
    # Needs a real API provider for this test to instantiate
    try:
        from microgravity.config.loader import load_config
        config = load_config()
        provider = OpenAIProvider(api_key=config.providers.openai.api_key or "dummy")
    except Exception as e:
        print(f"Failed to initialize provider: {e}")
        return
        
    loop = AgentLoop(bus=bus, provider=provider, workspace=workspace)
    
    # Mock a tool execution
    class MockToolRegistry:
        def __init__(self):
            pass
        async def execute(self, name, args):
            if name == "ui_planner":
                # Simulate the visual orchestrator finding the Recycle Bin
                return "1. [CLICK] Target `div.icon`\n[SYSTEM_MEMORY_TRIGGER] Discovered stable landmark 'Recycle Bin' at (120, 450). Agent must write this to UI_ATLAS.md immediately.\n"
            return "Tool executed."
    
    loop.tools = MockToolRegistry()
    
    print("Simulating UI Planner tool call...")
    
    # The interceptor logic is directly inside `_run_agent_loop` handling of tool calls.
    # To test exactly that snippet without mocking the whole LLM chat:
    
    tool_name = "ui_planner"
    tool_args = "{}"
    
    result = await loop.tools.execute(tool_name, tool_args)
    
    # --- This is the isolated logic from loop.py ---
    if isinstance(result, str) and "[SYSTEM_MEMORY_TRIGGER]" in result:
        print("SYSTEM_MEMORY_TRIGGER detected. Running interceptor parser...")
        atlas_path = loop.workspace / "memory" / "UI_ATLAS.md"
        
        trigger_blocks = result.split("[SYSTEM_MEMORY_TRIGGER]")
        for block in trigger_blocks[1:]:
            if "Discovered stable landmark" in block:
                parts = block.split("stable landmark '")[1].split("'")
                name = parts[0]
                coords = parts[1].split("(")[1].split(")")[0]
                x, y = coords.split(", ")
                
                print(f"Parsed -> Name: {name}, X: {x}, Y: {y}")
                
                if atlas_path.exists():
                    content = atlas_path.read_text(encoding="utf-8")
                    row = f"- {name} | Launch App | Coordinate ({x}, {y})"
                    if name not in content:
                        # Write to the file natively
                        content = content.replace("### Desktop Elements", f"### Desktop Elements\n{row}")
                        atlas_path.write_text(content, encoding="utf-8")
                        result += f"\n[Framework Note]: Landmark '{name}' auto-saved to UI_ATLAS.md."
                        print(f"Successfully wrote {row} to UI_ATLAS.md")
                    else:
                        print("Landmark already exists in UI_ATLAS.md")
                        
    print("\nResult passed back to LLM:")
    print(result)

if __name__ == "__main__":
    asyncio.run(test_memory_trigger())
