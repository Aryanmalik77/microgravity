import asyncio
import os
import sys
import traceback
from pathlib import Path
from loguru import logger

# Ensure project root is in path
sys.path.append(os.getcwd())

from src.memory.kernel import MemoryKernel
from src.intelligence.perception.engine import VisionEngine
from src.kernel.loop import KernelLoop
from src.capabilities.web.browser import HybridBrowserTool

async def verify_agentic_loop():
    workspace = Path.cwd()
    logger.info("--- Starting UI Agent Integration Verification ---")
    
    # API keys are now handled internally by components via load_config()

    kernel = None
    try:
        # 2. Initialize Components
        logger.info("[Verify] Initializing components...")
        memory = MemoryKernel(workspace / "storage")
        vision = VisionEngine(memory_kernel=memory)
        
        # Simple capabilities map
        browser = HybridBrowserTool(memory=memory)
        capabilities = {
            "browser": browser
        }
        
        kernel = KernelLoop(
            workspace=workspace,
            memory=memory,
            vision=vision,
            capabilities=capabilities,
            max_iterations=2 # Run a very short loop for verification
        )
        
        # 3. Run a simple observation task
        task = "Test Run: Verify closeup storage and coordinate resolution."
        logger.info(f"[Verify] Dispatched Task: {task}")
        
        # We run the task
        await kernel.run_task(task)
        
        logger.info("--- Verification Cycle Completed Successfully ---")

    except Exception as e:
        logger.error(f"[Verify] Failed: {e}")
        traceback.print_exc()
    finally:
        # Cleanup
        if kernel:
            logger.info("[Verify] Stopping kernel and background services...")
            kernel.stop()
            logger.info("[Verify] Kernel stopped.")
        else:
            logger.warning("[Verify] Kernel was never initialized.")

if __name__ == "__main__":
    # Ensure logs aren't too noisy
    log_file = "storage/logs/final_verification.log"
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    logger.add(log_file, rotation="10 MB")
    
    try:
        asyncio.run(verify_agentic_loop())
    except Exception as global_e:
        print(f"CRITICAL GLOBAL ERROR: {global_e}")
        traceback.print_exc()
