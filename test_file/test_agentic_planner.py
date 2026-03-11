"""
End-to-end test for the Agentic UI Planner & Executor.

This script tests the full agentic observe→decide→act→verify loop
using the UIAgent's new run_agentic() method.

Usage:
    python test_agentic_planner.py
    
    # Or with a custom task:
    python test_agentic_planner.py "Open Chrome and navigate to google.com"
"""

import sys
import os
import time
from pathlib import Path

# Add project root to path to load microgravity config
sys.path.append(os.getcwd())
from microgravity.config.loader import load_config

# API keys are now handled internally by components via load_config()

# Add project root and src to path
project_root = Path(os.getcwd())
sys.path.append(str(project_root / "src"))

from agent_core.ui_agent import UIAgent


def test_agentic_mode():
    """
    Tests the agentic planner with a real task.
    The agent will:
      1. Observe the current screen
      2. Ask Gemini for the next action (one at a time)
      3. Execute it
      4. Verify success
      5. Feed results back to the Live API
      6. Repeat until goal is complete
    """
    # Get task from command line or use default
    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
    else:
        task = "Open Notepad and type 'Hello World from Agentic Mode!'"
    
    print("=" * 60)
    print("  AGENTIC UI PLANNER TEST")
    print("=" * 60)
    print(f"\n  Task: {task}")
    print(f"  Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Initialize the agent
    print("\n[Test] Initializing UIAgent...")
    agent = UIAgent()
    
    # Run in agentic mode
    print(f"\n[Test] Starting agentic execution...")
    try:
        result = agent.run_agentic(task)
        print(f"\n[Test] Final result: {result}")
    except KeyboardInterrupt:
        print("\n[Test] Interrupted by user.")
    except Exception as e:
        print(f"\n[Test] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            agent.hud.stop()
        except:
            pass
    
    print("\n" + "=" * 60)
    print("  TEST COMPLETE")
    print("=" * 60)


def test_planner_only():
    """
    Tests just the AgenticPlanner without UIAgent (for unit testing the planning logic).
    """
    from planning.agentic_planner import AgenticPlanner
    from perception.screen import ScreenObserver
    
    print("[Test] Testing AgenticPlanner in isolation...\n")
    
    planner = AgenticPlanner()
    planner.set_goal("Open the Start Menu")
    
    # Capture a screenshot
    observer = ScreenObserver(output_dir=str(project_root / "debug_screenshots"))
    screenshot = observer.capture()
    
    if not screenshot:
        print("[Test] Failed to capture screenshot!")
        return
    
    print(f"[Test] Screenshot captured: {screenshot}")
    
    # Ask the planner for the next step
    print("[Test] Asking planner for next step...")
    action = planner.decide_next_step(screenshot)
    
    if action:
        print(f"\n[Test] Planner decided:")
        print(f"  Action: {action.get('action')}")
        print(f"  Target: {action.get('target', 'N/A')}")
        print(f"  Hint coords: {action.get('hint_coords', 'N/A')}")
        print(f"  Needs zoom: {action.get('needs_zoom', False)}")
        print(f"  Reasoning: {action.get('reasoning', 'N/A')}")
    else:
        print("[Test] Planner returned None (goal already complete or failed)")
    
    # Test verification
    print("\n[Test] Testing verification with same screenshot...")
    if action:
        success = planner.verify_step(action, screenshot)
        print(f"[Test] Verification result: {'SUCCESS' if success else 'FAILED'}")
    
    # Print step summary
    print(f"\n[Test] Step summary: {planner.get_step_summary()}")
    print(f"[Test] Full history:\n{planner.get_full_history_summary()}")


if __name__ == "__main__":
    if "--planner-only" in sys.argv:
        test_planner_only()
    else:
        test_agentic_mode()
