import re
from enum import IntEnum
from typing import Dict, Any, Tuple, Optional
from loguru import logger
from src.intelligence.planner.rules_engine import RulesEngine

class PowerLevel(IntEnum):
    """
    Role-Based Access Control for Swarm Agents.
    Level 0 is lowest (safest), Level 3 is highest (most dangerous).
    """
    OBSERVER = 0  # Read-only. DOM parsing, screenshots.
    OPERATOR = 1  # Safe UI actions. Click, scroll, drag.
    EXECUTOR = 2  # Destructive/Input actions. Type, submit, bash commands.
    ARCHITECT = 3 # System-level. Create agents, modify configurations.

class SafetyViolationError(Exception):
    """Raised when an agent attempts an action outside its power level."""
    pass

class SafetyInterceptor:
    """
    Evaluates intended actions before they are sent to the OS or Browser.
    Applies Non-Negotiable regex constraints and RBAC power level checks.
    """
    
    # Destructive or system-critical bash commands that are universally blocked
    NON_NEGOTIABLE_COMMANDS = [
        r"^rm -rf",
        r"^dd if=",
        r"^mkfs",
        r":\(\)\{.*:\|:&.*\};:", # Fork bomb (more flexible spacing)
        r"^wget.*chmod.*sh" # Remote script execution
    ]
    
    def __init__(self):
        self.rules_engine = RulesEngine()
        logger.info("[SafetyInterceptor] RulesEngine attached.")

    def evaluate_action(self, action_payload: Dict[str, Any], current_level: PowerLevel, context: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
        """
        Validates whether the payload is safe to execute given the current power level
        and situational rules.
        """
        context = context or {}
        action_type = str(action_payload.get("action") or "").lower()
        target = str(action_payload.get("target") or "").lower()
        value = action_payload.get("value", "")
        
        # 1. Observer Restrictions
        if current_level < PowerLevel.OPERATOR:
            if action_type in ["click", "scroll", "type", "submit", "run_terminal"]:
                return False, f"PowerLevel {current_level.name} cannot perform interactive action '{action_type}'."
                
        # 2. Operator Restrictions
        if current_level < PowerLevel.EXECUTOR:
            if action_type in ["type", "submit", "run_terminal"]:
                return False, f"PowerLevel {current_level.name} cannot perform state-mutating action '{action_type}'."
            # Protect sensitive fields even from simple clicks if defined
            if "password" in target or "auth" in target:
                 return False, f"PowerLevel {current_level.name} cannot interact with sensitive target '{target}'."
                 
        # 3. Universal Non-Negotiables (Even for Executors/Architects)
        if action_type == "run_terminal":
            for pattern in cls.NON_NEGOTIABLE_COMMANDS:
                if re.search(pattern, str(value)):
                    logger.critical(f"[INTERCEPTOR] BLOCKED MALICIOUS COMMAND: {value}")
                    return False, f"Action violates core Non-Negotiable safety directive: {pattern}"
                    
        # 4. Situational Rules Engine
        is_allowed, reason = self.rules_engine.evaluate_action(action_payload, context)
        if not is_allowed:
            return False, f"Situational Rule Violation: {reason}"
            
        # If all checks pass
        return True, "Action is safe."
