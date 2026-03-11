from typing import Dict, Any, Tuple
from loguru import logger

class AgentConfigManager:
    """
    Manages the dynamic configuration of the Agent during runtime.
    In a real implementation, this reads/writes to `config.json`.
    """
    def __init__(self):
        from microgravity.config.loader import load_config
        self._real_config = load_config()
        self.config = {
            "zoom_level": 1.0,
            "llm_provider": self._real_config.agents.defaults.model,
            "max_retries": self._real_config.agents.defaults.max_tool_iterations
        }

    def get_config(self) -> Dict[str, Any]:
        return self.config

    def increase_vision_zoom(self):
        """Programmatically increases zoom if vision targets are missed."""
        old_zoom = self.config["zoom_level"]
        new_zoom = min(old_zoom + 0.5, 3.0) # Max 300% zoom
        self.config["zoom_level"] = new_zoom
        logger.warning(f"[ConfigManager] Auto-tuning triggered: Zoom increased from {old_zoom}x to {new_zoom}x")
        # In reality: self.save_config_to_disk()

    def switch_to_pro_model(self):
        """Promotes the cognitive engine if reasoning fails repeatedly."""
        current = self.config["llm_provider"]
        if current != "gemini-2.5-pro":
            self.config["llm_provider"] = "gemini-2.5-pro"
            logger.warning(f"[ConfigManager] Auto-tuning triggered: Provider upgraded from {current} to gemini-2.5-pro")
            # In reality: self.save_config_to_disk()
