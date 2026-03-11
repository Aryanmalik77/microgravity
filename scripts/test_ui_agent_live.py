import asyncio
import os
import sys
import traceback
from pathlib import Path
from loguru import logger
from microgravity.config.loader import load_config

# Ensure project root is in path
sys.path.append(os.getcwd())

# API keys are now handled internally by components via load_config()

from src.memory.kernel import MemoryKernel
from src.intelligence.perception.engine import VisionEngine
from src.kernel.loop import KernelLoop
from src.capabilities.os.mouse import MouseTool
from src.capabilities.os.keyboard import KeyboardTool

async def run_live_test():
    workspace = Path.cwd()
    storage_dir = workspace / "storage"
    
    logger.info("--- Starting UI Agent LIVE Test ---")
    logger.info("Goal: Open Start menu and search for Notepad.")
    
    kernel = None
    try:
        # 1. Initialize Components
        memory = MemoryKernel(storage_dir)
        vision = VisionEngine(memory_kernel=memory)
        
        # Real capabilities
        mouse = MouseTool()
        keyboard = KeyboardTool()
        
        capabilities = {
            "mouse_control": mouse,
            "keyboard_control": keyboard
        }
        
        # 2. Setup Kernel Loop
        # We increase max_iterations to allowed for actual task completion
        kernel = KernelLoop(
            workspace=workspace,
            memory=memory,
            vision=vision,
            capabilities=capabilities,
            max_iterations=10
        )
        
        # 3. Dispatched Task
        task = "Open the Windows Start menu and type 'Notepad'."
        logger.info(f"[LiveTest] Dispatched: {task}")
        
        # 4. Run the loop
        # Note: This will take control of mouse/keyboard.
        await kernel.run_task(task)
        
        logger.info("--- LIVE Test Completed ---")

    except Exception as e:
        logger.error(f"[LiveTest] Failed: {e}")
        traceback.print_exc()
    finally:
        if kernel:
            logger.info("[LiveTest] Shutting down kernel...")
            kernel.stop()

if __name__ == "__main__":
    # Setup logging
    log_file = "storage/logs/live_test.log"
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    logger.add(log_file, rotation="10 MB")
    
    try:
        asyncio.run(run_live_test())
    except KeyboardInterrupt:
        logger.warning("Test interrupted by user.")
    except Exception as global_e:
        logger.error(f"CRITICAL ERROR: {global_e}")
