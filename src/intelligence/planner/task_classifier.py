from enum import Enum
from typing import Dict, Any

class TaskDeterminism(Enum):
    DETERMINISTIC = "DETERMINISTIC"
    SEMI_DETERMINISTIC = "SEMI_DETERMINISTIC"
    NON_DETERMINISTIC = "NON_DETERMINISTIC"

class TaskClassifier:
    """
    Evaluates a user prompt to determine its predictability.
    This dictates whether the loop needs heavy LLM OTA reasoning 
    or can bypass it for a fast procedural script.
    """
    
    # Simple heuristics. In V2, this will be an LLM API call.
    DETERMINISTIC_KEYWORDS = ["macro", "static", "export daily", "download report", "predefined", "fixed", "open", "launch", "start"]
    NON_DETERMINISTIC_KEYWORDS = ["research", "explore", "search web for", "find me", "unknown", "discover"]
    
    @classmethod
    def classify(cls, task_description: str, context: Optional[Dict[str, Any]] = None) -> TaskDeterminism:
        task_lower = task_description.lower()
        
        # 1. SPECIAL RULES (Fixed Overrides)
        # e.g. Safety-critical domains are always NON_DETERMINISTIC
        if any(domain in task_lower for domain in ["delete", "buy", "pay", "shutdown", "reformat"]):
            return TaskDeterminism.NON_DETERMINISTIC
            
        # 2. DETERMINISTIC Procedures (Known Macros)
        if any(keyword in task_lower for keyword in cls.DETERMINISTIC_KEYWORDS):
            return TaskDeterminism.DETERMINISTIC
            
        # 3. SEMI-DETERMINISTIC (Situational Conditionals)
        # "Book a flight", "Order food" - Flows are known but content is dynamic
        if any(keyword in task_lower for keyword in ["book", "order", "fill", "signup"]):
            return TaskDeterminism.SEMI_DETERMINISTIC

        # 4. EXPLORATORY (Non-Deterministic)
        if any(keyword in task_lower for keyword in cls.NON_DETERMINISTIC_KEYWORDS):
            return TaskDeterminism.NON_DETERMINISTIC
            
        return TaskDeterminism.SEMI_DETERMINISTIC
    
    @classmethod
    def get_routing_strategy(cls, task_description: str) -> Dict[str, Any]:
        """Returns a classification payload for the Dispatcher."""
        determinism = cls.classify(task_description)
        return {
            "determinism_level": determinism.value,
            "requires_full_ota": determinism == TaskDeterminism.NON_DETERMINISTIC or determinism == TaskDeterminism.SEMI_DETERMINISTIC,
            "can_use_macro": determinism == TaskDeterminism.DETERMINISTIC
        }
