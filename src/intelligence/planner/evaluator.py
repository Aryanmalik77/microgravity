from typing import Dict, Any
from loguru import logger
from src.kernel.config_manager import AgentConfigManager

class FeedbackEvaluator:
    """
    The Diagnostic loop that watches the Agent.
    If the Agent fails consecutive actions, this module steps in 
    and leverages the `AgentConfigManager` to auto-tune the params.
    """
    def __init__(self, config_manager: AgentConfigManager):
        self.config_manager = config_manager
        self.consecutive_failures = 0
        self.action_history = []

    def log_action_result(self, action: Dict[str, Any], success: bool, error_message: str = "") -> bool:
        """
        Receives feedback after an ACT phase.
        Returns True if a SYSTEM_RESTART flag is triggered by auto-tuning.
        """
        self.action_history.append({
            "action": action,
            "success": success,
            "error_message": error_message
        })

        if success:
            if self.consecutive_failures > 0:
                logger.success("[Evaluator] Agent recovered. Resetting failure count.")
            self.consecutive_failures = 0
            return False
            
        # Failed action
        self.consecutive_failures += 1
        logger.error(f"[Evaluator] Action Failed: {error_message} (Failure {self.consecutive_failures}/3)")
        
        return self._evaluate_session_health()

    def _evaluate_session_health(self) -> bool:
        """
        Checks if failures surpass the threshold and triggers a config edit.
        Returns True if the system needs a reboot/restart flag.
        """
        if self.consecutive_failures >= 3:
            logger.critical("[Evaluator] THRESHOLD REACHED: 3 consecutive failures. Initiating Diagnostic Auto-Tune...")
            
            # Analyze the last error to decide the fix
            last_error = self.action_history[-1].get("error_message", "").lower()
            
            if "not found" in last_error or "vision" in last_error or "bbox" in last_error:
                logger.info("[Evaluator] Diagnosis: Element too small or obscured. Mutating zoom_level.")
                self.config_manager.increase_vision_zoom()
            elif "parse" in last_error or "hallucination" in last_error:
                logger.info("[Evaluator] Diagnosis: Reasoning envelope exceeded. Mutating LLM provider.")
                self.config_manager.switch_to_pro_model()
            else:
                 logger.info("[Evaluator] Diagnosis: Unknown error cascade. Mutating LLM provider as safety fallback.")
                 self.config_manager.switch_to_pro_model()

            # We fixed the config. We return True so the KernelLoop knows to restart with new params.
            self.consecutive_failures = 0
            return True
            
        return False
