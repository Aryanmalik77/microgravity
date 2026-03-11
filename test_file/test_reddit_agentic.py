import sys
import os
import time
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent
sys.path.append(str(project_root / "ui_agent_engine" / "src"))

from agent_core.ui_agent import UIAgent

def run_reddit_test():
    print("==================================================")
    print("      Reddit Autonomous Task (Agentic Mode)")
    print("==================================================\n")
    
    # Initialize the fully aware agent
    agent = UIAgent()
    
    goal = (
        "Open Chrome, go to reddit.com. "
        "Log in with username 'Sea-Rate-8973' and password 'Ar@151203'. "
        "Then search for and visit multiple threads related to random video calling apps."
    )
    
    print(f"Goal: {goal}\n")
    
    try:
        # Run in fully autonomous agentic mode
        agent.run_agentic(goal)
    except KeyboardInterrupt:
        print("\n[!] Task interrupted by user.")
    except Exception as e:
        print(f"\n[-] Error during execution: {e}")
    finally:
        print("\n[!] Cleaning up...")
        if hasattr(agent, 'hud') and agent.hud:
            agent.hud.stop()
        if hasattr(agent, 'live_streamer') and agent.live_streamer:
            agent.live_streamer.stop()
            
    print("==================================================")

if __name__ == "__main__":
    # API keys are now handled internally by components via load_config()
             
    run_reddit_test()
