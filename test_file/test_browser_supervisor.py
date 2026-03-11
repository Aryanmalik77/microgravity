import asyncio
import os
import sys

# Force project root to avoid importing from microgravity
import os
import sys
current_dir = os.path.abspath(os.path.dirname(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Remove nanobot from sys.path if it's there
sys.path = [p for p in sys.path if 'nanobot' not in p.lower()]

from ui_agent_engine.src.agent_core.ui_agent import UIAgent

async def main():
    print("====================================")
    print("Testing Phase 7: Browser Tool Integration & Supervision")
    print("====================================")
    
    # Initialize UI Agent
    agent = UIAgent()
    
    # We set an explicit test objective that forces the agent to use the browser tool
    # For this test, we will bypass the actual planner LLM call and manually inject the intent
    # just to see the supervisory loop run.
    
    print("\n[Test] Running UIAgent with a web-centric objective...")
    
    try:
        # Run the full agentic loop. The planner should decide to use delegate_to_browser_tool
        objective = "You must delegate to the Browser Tool to navigate to https://example-saas.com and extract the pricing table."
        agent.run_agentic(objective)
            
    except KeyboardInterrupt:
        pass
    finally:
        agent.browser_tool.abort()
        print("Test finished.")

if __name__ == "__main__":
    asyncio.run(main())    
