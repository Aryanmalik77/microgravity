import asyncio
import sys
from pathlib import Path

# Add project root and src to path
project_root = Path(r"C:\Users\HP\Downloads\micro gravity - Copy")
sys.path.insert(0, str(project_root))

from src.kernel.config_manager import AgentConfigManager
from src.intelligence.planner.evaluator import FeedbackEvaluator

def test_auto_tuning():
    print("Testing Autonomous Feedback Loop & Auto-Tuning...\n")
    
    config = AgentConfigManager()
    evaluator = FeedbackEvaluator(config)
    
    # 1. Establish Baseline
    print("--- 1. Checking Baseline Configuration ---")
    initial_zoom = config.get_config()["zoom_level"]
    initial_model = config.get_config()["llm_provider"]
    assert initial_zoom == 1.0, "Initial zoom should be 1.0."
    assert initial_model == "gemini-2.5-flash", "Initial model should be flash."
    print("PASS: Baseline confirmed.\n")
    
    # 2. Simulate Temporary Failure & Recovery
    print("--- 2. Testing Temporary Failure Recovery ---")
    dummy_action = {"action": "click", "target": "submit_btn"}
    
    # Fail once
    evaluator.log_action_result(dummy_action, success=False, error_message="Network timeout")
    assert evaluator.consecutive_failures == 1
    
    # Succeed immediately after
    evaluator.log_action_result(dummy_action, success=True, error_message="")
    assert evaluator.consecutive_failures == 0
    print("PASS: Success signal successfully reset the failure counter.\n")
    
    # 3. Trigger Threshold Auto-Tune (Vision Error)
    print("--- 3. Testing Threshold Vision Auto-Tune ---")
    vision_error = "BBox for target not found on screen."
    
    needs_restart = evaluator.log_action_result(dummy_action, False, vision_error)
    assert not needs_restart # 1 fail
    needs_restart = evaluator.log_action_result(dummy_action, False, vision_error)
    assert not needs_restart # 2 fails
    
    # Third failure should trigger the Threshold
    needs_restart = evaluator.log_action_result(dummy_action, False, vision_error)
    
    assert needs_restart == True, "Evaluator did not request a system restart after 3 failures!"
    
    new_zoom = config.get_config()["zoom_level"]
    assert new_zoom == 1.5, f"Config Manager failed to mutate zoom. Zoom is {new_zoom}."
    print(f"PASS: Evaluator caught 3 vision errors and autonomously mutated zoom to {new_zoom}x.\n")
    
    # 4. Trigger Threshold Auto-Tune (Cognitive Error)
    print("--- 4. Testing Threshold Cognitive Auto-Tune ---")
    cognitive_error = "LLM Hallucination: Action schema could not be parsed."
    
    # Fail 3 times with reasoning error
    evaluator.log_action_result(dummy_action, False, cognitive_error)
    evaluator.log_action_result(dummy_action, False, cognitive_error)
    needs_restart = evaluator.log_action_result(dummy_action, False, cognitive_error)
    
    assert needs_restart == True
    new_model = config.get_config()["llm_provider"]
    assert new_model == "gemini-2.5-pro", f"Failed to promote model. Current is {new_model}."
    print(f"PASS: Evaluator caught 3 cognitive errors and promoted engine to '{new_model}'.\n")
    
    print("All Auto-Tuning Tests Passed Successfully!")

if __name__ == "__main__":
    test_auto_tuning()
