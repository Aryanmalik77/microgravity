import sys
import os
import asyncio
import time
from pathlib import Path
from loguru import logger

# Add project root to sys.path
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

# API keys are now handled internally by components via load_config()

from src.memory.kernel import MemoryKernel
from src.intelligence.perception.engine import VisionEngine
from src.kernel.loop import KernelLoop
from src.capabilities.os.mouse import MouseTool
from src.capabilities.os.keyboard import KeyboardTool
from src.capabilities.web.browser import HybridBrowserTool
from src.kernel.interceptor import PowerLevel

async def run_github_test():
    workspace = Path.cwd()
    storage_dir = workspace / "storage"
    
    logger.info("--- Starting UI Agent GITHUB Task ---")
    logger.info("Goal: Open GitHub, Sign in with Google, and Search for openclaw.")

    # 1. Initialize Components
    memory = MemoryKernel(storage_dir)
    vision = VisionEngine(memory_kernel=memory, model_name="gemini-2.0-flash")
    
    # Real capabilities
    mouse = MouseTool()
    keyboard = KeyboardTool()
    browser = HybridBrowserTool(memory=memory)
    
    capabilities = {
        "mouse_control": mouse,
        "keyboard_control": keyboard,
        "web_browser": browser
    }
    
    # 2. Setup Kernel Loop
    loop = KernelLoop(
        workspace=workspace,
        memory=memory,
        vision=vision,
        capabilities=capabilities,
        max_iterations=20,
        power_level=PowerLevel.EXECUTOR
    )
    
    # 3. Dispatched Task
    objective = (
        "Open Google Chrome, navigate to https://github.com, "
        "click 'Sign in', choose 'Sign in with Google', "
        "complete the sign-in process, and then search for the 'openclaw' repository."
    )
    
    logger.info(f"[GitHubTest] Dispatched: {objective}")
    
    try:
        await loop.run_task(objective)
    except Exception as e:
        logger.error(f"[GitHubTest] Loop failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        logger.info("--- GITHUB Task Completed ---")
        loop.stop()

if __name__ == "__main__":
    # Ensure logs directory exists
    Path("storage/logs").mkdir(parents=True, exist_ok=True)
    
    # Configure logger for the test
    logger.add("storage/logs/github_test.log", rotation="10 MB")
    
    try:
        asyncio.run(run_github_test())
    except KeyboardInterrupt:
        logger.warning("Test interrupted by user.")
    except Exception as global_e:
        logger.error(f"CRITICAL ERROR: {global_e}")
