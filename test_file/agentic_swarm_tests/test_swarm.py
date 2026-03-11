import sys
import os

# Ensure the agentic_swarm package is in the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging
from unittest.mock import MagicMock
from core.memory import MemoryAdapter
from core.operator import SeekingOperator, OperatorPlanSchema

# Configure extremely basic logging to verify execution
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(name)s - %(message)s")

def test_operator_instantiation():
    """Validates the Swarm framework initializes without module/syntax errors."""
    print("Initializing Agent Swarm System...")
    memory = MemoryAdapter()
    
    # Mock the LLM to prevent actual API calls during CI/CD tests
    operator = SeekingOperator(memory=memory)
    operator.pipeline.execute_with_validation = MagicMock(return_value=OperatorPlanSchema(
        selected_agent="SystemSeeker",
        sub_objective="Run `dir` to list files.",
        reasoning="Testing execution."
    ))
    
    operator.agent_registry["SystemSeeker"].execute = MagicMock(return_value={
        "status": "success",
        "agent": "SystemSeeker",
        "result": {"return_code": 0, "output": "Directory listing successful."}
    })
    
    # Run Orchestrator
    result = operator.orchestrate(user_objective="List all files in the current directory.")
    
    print("\n--- TEST RESULT ---")
    print(f"Status: {result['status']}")
    print(f"Ledger Trace: {memory.get_execution_history()}")
    
    assert result["status"] == "completed"
    assert len(memory.get_execution_history()) == 1
    
    print("\nSwarm architecture successfully scaffolded and verified!")

if __name__ == "__main__":
    test_operator_instantiation()
