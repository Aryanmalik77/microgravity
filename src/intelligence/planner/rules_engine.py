import re
from typing import Dict, Any, List, Optional
from loguru import logger

class RuleType:
    GENERAL = "GENERAL"
    SPECIAL = "SPECIAL"

class SituationalRule:
    def __init__(self, rule_id: str, pattern: str, action_type: str, allowed: bool, reasoning: str, rule_type: str = RuleType.GENERAL):
        self.rule_id = rule_id
        self.pattern = pattern # Regex to match against URL or Domain
        self.action_type = action_type # e.g. "click", "delete", "buy"
        self.allowed = allowed
        self.reasoning = reasoning
        self.rule_type = rule_type

class RulesEngine:
    """
    Cognitive Rules Engine for the MICROGRAVITY Swarm.
    Discards or allows actions based on conditionals and situational context.
    """
    def __init__(self):
        self.rules: List[SituationalRule] = []
        self._load_default_rules()

    def _load_default_rules(self):
        # General Rules (Global)
        self.rules.append(SituationalRule(
            "G1_COOKIE_CONSENT",
            r".*", 
            "click", 
            True, 
            "Always attempt to resolve cookie banners.",
            RuleType.GENERAL
        ))
        
        # Special Rules (Context-Specific)
        self.rules.append(SituationalRule(
            "S1_NO_DELETE_PRODUCTION",
            r"dashboard\.corporate\.com", 
            "delete", 
            False, 
            "Deletion is strictly prohibited on production dashboards.",
            RuleType.SPECIAL
        ))

    def evaluate_action(self, action: Dict[str, Any], context: Dict[str, Any]) -> tuple[bool, str]:
        """
        Evaluates an action against the internal ruleset.
        Special Rules always override General Rules.
        Returns (is_allowed, reason).
        """
        domain = context.get("domain", "unknown")
        action_type = action.get("action", "unknown").lower()
        
        applicable_rules = []
        for rule in self.rules:
            if re.search(rule.pattern, domain) and (rule.action_type == "*" or rule.action_type == action_type):
                applicable_rules.append(rule)
        
        if not applicable_rules:
            return True, "No applicable rules. Action allowed."

        # Sort: Special Rules first
        applicable_rules.sort(key=lambda r: 0 if r.rule_type == RuleType.SPECIAL else 1)
        
        for rule in applicable_rules:
            if not rule.allowed:
                logger.warning(f"[RulesEngine] Action BLOCKED by {rule.rule_id}: {rule.reasoning}")
                return False, rule.reasoning
            
        return True, "Action allowed by ruleset."

    def add_rule(self, rule: SituationalRule):
        self.rules.append(rule)
        logger.info(f"[RulesEngine] Added new rule: {rule.rule_id}")
