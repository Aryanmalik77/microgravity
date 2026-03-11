import os
import sys
import logging
import asyncio
from pathlib import Path

# Add Agentic/agentic_swarm and ui_agent_engine/src to path
project_root = Path(__file__).parent
sys.path.append(str(project_root / "Agentic" / "agentic_swarm"))

from core.operator import SeekingOperator
from core.memory import MemoryAdapter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("GitHubSwarmTest")

async def run_integration_test():
    print("DEBUG: Entered run_integration_test", flush=True)
    print("==================================================")
    print("   GitHub Swarm & UI Agent Integration Test")
    print("==================================================\n", flush=True)

    try:
        # Set up environment
        print("[0] Setting up environment...", flush=True)
        # API keys are now handled internally by components via load_config()
        
        # 1. Initialize Swarm Operator
        print("[1] Initializing Swarm Seeker Operator...", flush=True)
        memory = MemoryAdapter()
        operator = SeekingOperator(memory=memory, model_name="gpt-4o")
        print("[1.1] Operator initialized successfully.", flush=True)
        
        objective = (
            "Perform a high-fidelity integration test on GitHub: "
            "1. Login to github.com using 'Sign in with Google' ONLY. "
            "2. Logout and Re-login via Google to verify session persistence. "
            "3. Find the 'openclaw' repository. "
            "4. Clone the repository."
        )
        
        print(f"\n[2] Dispatching Objective to Swarm:\n'{objective}'\n", flush=True)
        
        print("[3] Starting Orchestration loop...", flush=True)
        result = operator.orchestrate(objective, max_steps=10)
        print(f"\n[4] Swarm Execution Result: {result.get('status', 'Unknown')}", flush=True)

    except Exception as e:
        print(f"\n[CRITICAL ERROR] Integration Test Failed: {type(e).__name__}: {e}", flush=True)
        import traceback
        traceback.print_exc()
    except BaseException as be:
        print(f"\n[SYSTEM ERROR] Caught BaseException: {type(be).__name__}: {be}", flush=True)
        import traceback
        traceback.print_exc()

    print("\n[5] Integration Test Complete.", flush=True)
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(run_integration_test())
