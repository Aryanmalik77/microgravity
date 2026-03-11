import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from loguru import logger
from src.memory.store import PersistentStore

class UIProfileStore:
    """
    Manages Temporary (Session) and Permanent (Macro) procedural UI profiles.
    Allows the agentic system to bypass LLM cognitive loops for predictable tasks.
    """
    def __init__(self, storage: PersistentStore):
        self.storage = storage
        self.session_path = "memory/profiles/sessions"
        self.macro_path = "memory/profiles/macros"

    # --- Temporary Profiles (Short-Term Memory) ---
    def save_session_profile(self, session_id: str, profile_data: Dict[str, Any]) -> None:
        """Stores ephemeral UI state for a specific task session."""
        path = f"{self.session_path}/{session_id}.json"
        self.storage.write_json(path, profile_data)
        logger.debug(f"[UIProfileStore] Saved temporary session profile: {session_id}")

    def get_session_profile(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves ephemeral UI state."""
        path = f"{self.session_path}/{session_id}.json"
        return self.storage.read_json(path)

    def clear_session(self, session_id: str) -> None:
        """Flushes temporary memory after a task is complete."""
        path = f"{self.session_path}/{session_id}.json"
        if self.storage.exists(path):
            self.storage.write_json(path, {})
            logger.debug(f"[UIProfileStore] Flushed session profile: {session_id}")

    # --- Permanent Procedural Macros (Long-Term Memory) ---
    def save_permanent_macro(self, macro_name: str, sequence: List[Dict[str, Any]]) -> None:
        """Stores a confirmed, deterministic sequence of actions."""
        safe_name = macro_name.lower().replace(" ", "_").replace("/", "_")
        path = f"{self.macro_path}/{safe_name}.json"
        
        payload = {
            "macro_name": macro_name,
            "type": "DETERMINISTIC_SEQUENCE",
            "sequence": sequence
        }
        self.storage.write_json(path, payload)
        logger.info(f"[UIProfileStore] Saved permanent macro: {macro_name}")

    def get_permanent_macro(self, macro_name: str) -> Optional[Dict[str, Any]]:
        """Retrieves a saved procedural macro."""
        safe_name = macro_name.lower().replace(" ", "_").replace("/", "_")
        path = f"{self.macro_path}/{safe_name}.json"
        return self.storage.read_json(path)

    def _list_all_macros(self) -> List[Path]:
        """Scans the macro directory and returns all saved macro file paths."""
        macro_dir = self.storage.root / self.macro_path
        if not macro_dir.exists():
            return []
        return list(macro_dir.glob("*.json"))

    def find_macro_for_task(self, task_description: str) -> Optional[Dict[str, Any]]:
        """
        Dynamically scans saved macros and scores them against the task description
        using keyword overlap. Returns the best match if score exceeds threshold.
        """
        task_tokens = set(re.findall(r'[a-z]+', task_description.lower()))
        # Filter out common stop words
        stop_words = {"the", "a", "an", "is", "to", "for", "and", "of", "in", "on", "it", "me", "my", "run", "please", "do"}
        task_tokens -= stop_words
        
        best_match = None
        best_score = 0
        
        for macro_file in self._list_all_macros():
            macro_data = self.storage.read_json(str(macro_file.relative_to(self.storage.root)))
            if not macro_data:
                continue
                
            # Score by keyword overlap between task tokens and macro name tokens
            macro_name = macro_data.get("macro_name", macro_file.stem)
            macro_tokens = set(re.findall(r'[a-z]+', macro_name.lower()))
            
            overlap = task_tokens & macro_tokens
            score = len(overlap)
            
            if score > best_score:
                best_score = score
                best_match = macro_data
                
        # Require at least 2 keyword overlaps to prevent false positives
        if best_score >= 2:
            logger.info(f"[UIProfileStore] Macro matched with score {best_score}: '{best_match['macro_name']}'")
            return best_match
            
        logger.debug(f"[UIProfileStore] No macro matched for task (best score: {best_score}).")
        return None
