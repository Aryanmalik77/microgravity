"""
Test script for Multi-Tab Management & Proactive Discovery.

This test verifies:
1. In-place execution (attaching to an existing window without restart)
2. Tab scanning (switching between tabs to find information)
3. Proactive discovery (suggesting features from other tabs)

Usage:
    # 1. Open Chrome manually with at least 3 tabs (e.g., Google, YouTube, Wikipedia)
    # 2. Run this test
    python test_tab_discovery.py "Find the tab about YouTube and tell me what the other tabs are about."
"""

import sys
import os
import time
from pathlib import Path

# Add project root and src to path
project_root = Path(r"C:\Users\HP\Downloads\micro gravity - Copy\ui_agent_engine")
sys.path.append(str(project_root / "src"))

from agent_core.ui_agent import UIAgent

def test_multi_tab():
    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
    else:
        task = "Find the Chrome tab about 'Google' and then suggest what other options or features you see in the other open tabs."
    
    print("=" * 60)
    print("  MULTI-TAB MANAGEMENT & DISCOVERY TEST")
    print("=" * 60)
    print(f"\n  Task: {task}")
    print("=" * 60)
    
    # Initialize the agent
    print("\n[Test] Initializing UIAgent...")
    agent = UIAgent()
    
    # Run in agentic mode
    print(f"\n[Test] Starting agentic execution (IN-PLACE)...")
    try:
        # Note: UIAgent.run_agentic now includes window-attachment logic
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

if __name__ == "__main__":
    test_multi_tab()
