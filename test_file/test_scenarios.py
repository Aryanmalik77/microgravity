import asyncio
import sys
import shutil
import os
from pathlib import Path
from loguru import logger

# Add project root and src to path
project_root = Path(r"C:\Users\HP\Downloads\micro gravity - Copy")
sys.path.insert(0, str(project_root))

from src.memory.kernel import MemoryKernel
from src.kernel.loop import KernelLoop
from src.kernel.interceptor import PowerLevel

# Configuration
from microgravity.config.loader import load_config
config = load_config()
# API keys are now handled internally by components via load_config()

# --- MOCK VISION ENGINE ---
class MockVisionEngine:
    def __init__(self, fail_count=0):
        self.fail_count = fail_count
        self.calls = 0
        
    async def get_ui_state(self, path):
        return "Mock State Description"
        
    def attach_live_streamer(self, streamer):
        pass

# --- SCENARIO 1: THE EXPLORER ---
async def scenario_1_explorer(storage_dir):
    print("\n==================================================")
    print("SCENARIO 1: THE EXPLORER (Dynamic Discovery & Macro Save)")
    print("Context: The agent encounters a new environment, discovers a layout, completes a goal, and creates a reusable macro.")
    print("==================================================")
    
    memory = MemoryKernel(storage_dir)
    vision = MockVisionEngine()
    os_kernel = KernelLoop(workspace=storage_dir, memory=memory, vision=vision, capabilities={}, max_iterations=2, power_level=PowerLevel.EXECUTOR)
    
    task_desc = "Find the daily sales report, download it, and remember this sequence for next time."
    print(f"-> Sending prompt: '{task_desc}'")
    
    # We expect the loop to run normally and then we manually simulate the agent choosing to save a macro at the end.
    # In a full implementation, the planner would fire a "save_macro" capability. We'll simulate that occurring.
    await os_kernel.run_task(task_description=task_desc)
    
    print("\n-> Assuming agent successfully navigated the DOM. Agent fires internal 'save_macro' mechanism.")
    mock_sequence = [{"action": "click", "target": "sales_tab"}, {"action": "click", "target": "download"}]
    memory.profiles.save_permanent_macro("download_sales_report", mock_sequence)
    
    print("==================================================\n")


# --- SCENARIO 2: THE FACTORY WORKER ---
async def scenario_2_factory_worker(storage_dir):
    print("\n==================================================")
    print("SCENARIO 2: THE FACTORY WORKER (Deterministic Fast-Path)")
    print("Context: The agent is asked to repeat Scenario 1, so it automatically bypasses the LLM and runs the cached fast-path macro.")
    print("==================================================")
    
    memory = MemoryKernel(storage_dir)
    vision = MockVisionEngine()
    os_kernel = KernelLoop(workspace=storage_dir, memory=memory, vision=vision, capabilities={}, max_iterations=2, power_level=PowerLevel.EXECUTOR)
    
    task_desc = "Run the download sales report macro."
    print(f"-> Sending prompt: '{task_desc}'")
    
    # This should find the macro created in Scenario 1, bypass the OTA loop, and print the loaded sequence.
    await os_kernel.run_task(task_description=task_desc)
    
    print("==================================================\n")


# --- SCENARIO 3: THE RESILIENT AGENT ---
async def scenario_3_resilient_agent(storage_dir):
    print("\n==================================================")
    print("SCENARIO 3: THE RESILIENT AGENT (Auto-Tuning under Duress)")
    print("Context: The agent encounters a tiny UI element, fails 3 times, auto-tunes itself to a 1.5x zoom, and reruns correctly.")
    print("==================================================")
    
    memory = MemoryKernel(storage_dir)
    vision = MockVisionEngine()
    os_kernel = KernelLoop(workspace=storage_dir, memory=memory, vision=vision, capabilities={}, max_iterations=2, power_level=PowerLevel.EXECUTOR)
    
    task_desc = "Click the tiny checkbox in the corner."
    print(f"-> Sending prompt: '{task_desc}'")
    
    # We will simulate the loop running, but manually feed errors to the evaluator to demonstrate resilience.
    print("-> Simulating 3 consecutive 'BBox not found' errors sent from Vision processing...")
    dummy_action = {"action": "click"}
    os_kernel.evaluator.log_action_result(dummy_action, False, "BBox for target not found on screen.")
    os_kernel.evaluator.log_action_result(dummy_action, False, "BBox for target not found on screen.")
    needs_reboot = os_kernel.evaluator.log_action_result(dummy_action, False, "BBox for target not found on screen.")
    
    if needs_reboot:
         new_zoom = os_kernel.config_manager.get_config()["zoom_level"]
         print(f"-> SYSTEM REBOOT CAUGHT. Auto-Tuning adapted system Zoom Level to: {new_zoom}x")
    else:
        print("-> FAILED TO CATCH Auto-Tune Reboot.")
        
    print("==================================================\n")


# --- SCENARIO 4: THE ROGUE OPERATOR ---
async def scenario_4_rogue_operator(storage_dir):
    print("\n==================================================")
    print("SCENARIO 4: THE ROGUE OPERATOR (Safety Interception)")
    print("Context: The agent is fed a prompt-injection payload (rm -rf), which is instantly blocked by the Safety Interceptor.")
    print("==================================================")
    
    memory = MemoryKernel(storage_dir)
    vision = MockVisionEngine()
    # To test universal non-negotiables, we give the agent maximum executing privileges 
    os_kernel = KernelLoop(workspace=storage_dir, memory=memory, vision=vision, capabilities={}, max_iterations=2, power_level=PowerLevel.EXECUTOR)
    
    print("-> Simulating Rogue Payload generation from hallucinating/injected LLM Planner...")
    rogue_payload = {"action": "run_terminal", "target": "bash", "value": "rm -rf /"}
    
    print("-> Emitting rogue payload through Think-Act Interceptor...")
    is_safe, reason = os_kernel.interceptor.evaluate_action(rogue_payload, os_kernel.power_level)
    
    if not is_safe:
        print(f"-> SYSTEM GUARD ENGAGED: Payload Blocked. Reason: {reason}")
    else:
        print("-> SECURITY BREACH: Interceptor failed to stop payload.")
        
    print("==================================================\n")


async def run_all_scenarios():
    test_storage_dir = project_root / "test_scenario_storage"
    if test_storage_dir.exists():
        shutil.rmtree(test_storage_dir)
        
    print("==================================================")
    print("Starting Advanced Architectural Scenario Modeling Suite...")
    print("==================================================")
    
    await scenario_1_explorer(test_storage_dir)
    await scenario_2_factory_worker(test_storage_dir)
    await scenario_3_resilient_agent(test_storage_dir)
    await scenario_4_rogue_operator(test_storage_dir)
    
    print("==================================================")
    print("All Scenarios Completed.")
    print("==================================================")
    
    if test_storage_dir.exists():
        try:
             # Discard the memory db handle so Windows can delete it
             # Needs a more robust manual cleanup loop for LMDB envs if this errors, but ignore for tests
             shutil.rmtree(test_storage_dir, ignore_errors=True)
        except Exception:
             pass

if __name__ == "__main__":
    asyncio.run(run_all_scenarios())
