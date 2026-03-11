from typing import List, Dict, Any, Optional
from loguru import logger
from src.intelligence.planner.task_classifier import TaskClassifier

class IntelligenceDispatcher:
    """
    The decision engine that routes tasks to different modalities.
    It evaluates whether a task requires:
    - Code execution / Shell (TEXTUAL)
    - Web automation (WEB)
    - Native OS interaction (VISUAL)
    - And determines the predictability (Determinism) of the task.
    """
    def __init__(self, provider: Any):
        self.provider = provider
        self.classifier = TaskClassifier()

    async def determine_strategy(self, task: str, screen_available: bool = True) -> Dict[str, Any]:
        """
        Analyzes the task and environmental state to pick the best execution strategy.
        """
        logger.info(f"[Dispatcher] Analyzing task: {task[:50]}...")
        
        # Determine the predictability of the task
        classification = self.classifier.get_routing_strategy(task)
        logger.info(f"[Dispatcher] Classification Strategy: {classification['determinism_level']}")
        
        # Base strategy setup
        strategy = classification.copy()
        
        if "click" in task.lower() or "screen" in task.lower() or "open" in task.lower():
            if screen_available:
                strategy.update({"modality": "VISUAL", "confidence": 0.9, "reason": "Task implies UI interaction."})
                return strategy
        
        strategy.update({"modality": "TEXTUAL", "confidence": 0.8, "reason": "Defaulting to textual reasoning."})
        return strategy

    async def decompose_to_steps(self, task: str, strategy: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Breaks down a task into actionable steps based on the chosen strategy.
        """
        logger.info(f"[Dispatcher] Decomposing task into {strategy['modality']} steps.")
        return []
