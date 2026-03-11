import asyncio
import os
import sys
from pathlib import Path

# Add project root and src to path
project_root = Path(r"C:\Users\HP\Downloads\micro gravity - Copy")
sys.path.insert(0, str(project_root))

from src.intelligence.planner.task_classifier import TaskClassifier, TaskDeterminism
from src.intelligence.planner.dispatcher import IntelligenceDispatcher

async def test_classification_engine():
    print("Testing Task Classifier Engine...\n")
    
    # 1. Test TaskClassifier directly
    print("--- Direct Classifier Test ---")
    deterministic_tasks = [
        "export daily sales report to csv",
        "run the predefined static macro on github",
        "download report from the dashboard"
    ]
    
    non_deterministic_tasks = [
        "research the top 5 competitors parsing pricing",
        "explore this new SaaS dashboard and find the billing settings",
        "search web for the latest artificial intelligence news"
    ]
    
    semi_tasks = [
        "book a flight to New York",
        "buy me a coffee on this website",
        "login to facebook"
    ]

    for task in deterministic_tasks:
        result = TaskClassifier.classify(task)
        assert result == TaskDeterminism.DETERMINISTIC, f"Failed: {task} -> {result}"
        print(f"PASS: '{task[:30]}...' -> {result}")

    for task in non_deterministic_tasks:
        result = TaskClassifier.classify(task)
        assert result == TaskDeterminism.NON_DETERMINISTIC, f"Failed: {task} -> {result}"
        print(f"PASS: '{task[:30]}...' -> {result}")

    for task in semi_tasks:
        result = TaskClassifier.classify(task)
        assert result == TaskDeterminism.SEMI_DETERMINISTIC, f"Failed: {task} -> {result}"
        print(f"PASS: '{task[:30]}...' -> {result}")

    # 2. Test Dispatcher Integration
    print("\n--- Dispatcher Integration Test ---")
    dispatcher = IntelligenceDispatcher(provider=None)
    
    # Test a deterministic prompt
    strategy_d = await dispatcher.determine_strategy("export daily macro", screen_available=False)
    assert strategy_d["determinism_level"] == "DETERMINISTIC"
    print("PASS: Dispatcher evaluated Deterministic Strategy correctly.")
    
    # Test a non-deterministic UI prompt
    strategy_nd = await dispatcher.determine_strategy("explore and click the billing link", screen_available=True)
    assert strategy_nd["determinism_level"] == "NON_DETERMINISTIC"
    assert strategy_nd["modality"] == "VISUAL"
    print("PASS: Dispatcher evaluated Non-Deterministic Visual Strategy correctly.")
    
    print("\nAll Classification Engine Tests Passed Successfully!")

if __name__ == "__main__":
    asyncio.run(test_classification_engine())
