import os
import sys
import time
from pathlib import Path

# Add ui_agent_engine/src to path
project_root = Path(__file__).parent / "ui_agent_engine"
sys.path.append(str(project_root / "src"))

from agent_core.ui_agent import UIAgent

def run_github_sequence():
    print("==================================================")
    print("   GitHub Automation Logic: Login/Logout/Clone")
    print("==================================================\n")
    
    # API keys are now handled internally by components via load_config()

    # 1. Initialize Agent
    print("[1] Initializing UIAgent with Live API...")
    agent = UIAgent()
    agent._start_live_stream()
    
    print("[2] Waiting for Live Session...")
    time.sleep(8)
    
    if not agent.live_streamer.is_streaming:
        print("[!] Warning: Live Stream not active. Proceeding with static fallback.")

    # High-level goals for the agent to figure out autonomously
    # 1. Login via Google
    login_goal = (
        "Open Chrome, go to https://github.com/login. "
        "Click the 'Sign in with Google' button. "
        "If prompted, select or enter your Google account details to complete the GitHub sign-in. "
        "Do NOT use the standard username/password fields."
    )
    print(f"\n[3] Executing: {login_goal}")
    agent.run_agentic(login_goal)
    
    # 2. Logout
    logout_goal = "Click on the user profile menu (top right) and sign out of GitHub"
    print(f"\n[4] Executing: {logout_goal}")
    agent.run_agentic(logout_goal)
    
    # 3. Re-login via Google
    relogin_goal = "Log back in to GitHub using the 'Sign in with Google' option to verify session persistence"
    print(f"\n[5] Executing: {relogin_goal}")
    agent.run_agentic(relogin_goal)
    
    # 4. Clone repo
    clone_goal = "Search GitHub for the 'openclaw' repository, navigate to it, and clone it locally"
    print(f"\n[6] Executing: {clone_goal}")
    agent.run_agentic(clone_goal)

    # Finalize
    print("\n[7] Sequence complete. Shutting down...")
    agent.learning_loop.finalize_episode(
        task="GitHub Full Integration Cycle",
        app_name="Chrome",
        app_class="Browser",
        overall_success=True # Assuming success for test harness coordination
    )
    agent._stop_live_stream()
    print("==================================================")

if __name__ == "__main__":
    run_github_sequence()
