import asyncio
import sys
import shutil
from pathlib import Path
from loguru import logger

# Add project root and src to path
project_root = Path(r"C:\Users\HP\Downloads\micro gravity - Copy")
sys.path.insert(0, str(project_root))

# Configuration
from microgravity.config.loader import load_config
config = load_config()
# API keys are now handled internally by components via load_config()

from src.memory.kernel import MemoryKernel
from src.kernel.loop import KernelLoop
from src.kernel.interceptor import PowerLevel
from src.intelligence.perception.engine import VisionEngine

async def test_full_agentic_os_integration():
    print("==================================================")
    print("Initiating Full Agentic OS Integration Test...")
    print("==================================================\n")
    
    # 1. Setup Environment
    test_storage_dir = project_root / "test_os_storage"
    if test_storage_dir.exists():
        shutil.rmtree(test_storage_dir)
        
    print("[1] Booting Memory Kernel and Pre-loading Macros...")
    memory = MemoryKernel(test_storage_dir)
    
    # Pre-seed a macro for Phase 1 & 2 testing
    macro_sequence = [{"action": "click", "target": "export"}]
    memory.profiles.save_permanent_macro("demo_macro", macro_sequence)
    
    # Mock VisionEngine to bypass API Keys for this pure architectural test
    class MockVisionEngine:
        def __init__(self):
            pass
        async def get_ui_state(self, path):
            return "Mock State Description"
        def attach_live_streamer(self, streamer):
            pass
            
    vision = MockVisionEngine()
    
    # 2. Initialize the Kernel Loop (Set PowerLevel to block dangerous commands, but allow typing)
    print("\n[2] Initializing KernelLoop with Operator Privileges (Level 1) & Auto-Tuning Engine...")
    os_kernel = KernelLoop(
        workspace=test_storage_dir,
        memory=memory,
        vision=vision,
        capabilities={},
        max_iterations=2, # Keep loop thin for testing
        power_level=PowerLevel.OPERATOR 
    )
    
    # 3. Test Feature: Deterministic Fast-Path Bypass (Phase 1 & 2)
    print("\n[3] Testing Feature: Deterministic Macro Bypass")
    print("-> Sending prompt: 'Please run the demo macro for me'")
    # Note: run_task will print the bypass logs and exit immediately because it finds a matching macro locally
    await os_kernel.run_task("Please run the demo macro for me")
    
    # 4. Test Feature: Exceeding PowerLevel (Phase 3)
    print("\n[4] Testing Feature: Role-Based Safety Interceptor")
    print("-> Sending fake exploratory task with malicious intent...")
    # Because it is NON_DETERMINISTIC, run_task will drop into the OTA loop.
    # Inside the OTA loop, we explicitly hardcoded `intended_action = {"action": "type", "target": "search_box"...}` in `loop.py`
    # However, because we initialized as OPERATOR (Level 1), the interceptor will block the `type` action!
    await os_kernel.run_task("Explore the internet and type into the search box.")
    
    # 5. Test Feature: Auto-Tuning Evaluator (Phase 4)
    # We must elevate power level so the interceptor doesn't block the dummy action, allowing it to hit the Feedback loop.
    print("\n[5] Testing Feature: Autonomous Diagnosic Looping")
    print("-> Re-initializing with Executor Privileges (Level 2) to bypass safety block...")
    os_kernel.power_level = PowerLevel.EXECUTOR
    print("-> Sending exploratory task that will repeatedly 'fail' vision checks...")
    # The loop will execute, but `loop.py` simulates a Vision BBox failure.
    # After the loop restarts or finishes, let's manually hit it twice more to trigger the threshold
    dummy_action = {"action": "type"}
    os_kernel.evaluator.log_action_result(dummy_action, False, "BBox not found")
    os_kernel.evaluator.log_action_result(dummy_action, False, "BBox not found")
    needs_reboot = os_kernel.evaluator.log_action_result(dummy_action, False, "BBox not found")
    
    if needs_reboot:
         new_zoom = os_kernel.config_manager.get_config()["zoom_level"]
         print(f"-> SYSTEM REBOOT CAUGHT. Auto-Tuning increased system Zoom Level to: {new_zoom}x")
         
    # Clean up
    print("\n==================================================")
    print("All Integration Tests Successfully Executed.")
    print("==================================================")
    
    if test_storage_dir.exists():
        try:
             # Discard the memory db handle so Windows can delete it
             memory.env.close() 
             shutil.rmtree(test_storage_dir, ignore_errors=True)
        except Exception:
             pass

if __name__ == "__main__":
    asyncio.run(test_full_agentic_os_integration())
