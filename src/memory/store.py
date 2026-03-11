import os
import json
from pathlib import Path
from typing import Optional, Any

class PersistentStore:
    """
    Handles low-level file persistence for the Agentic OS.
    Supports atomic writes and basic storage primitives.
    """
    def __init__(self, storage_root: Path):
        self.root = storage_root
        self.root.mkdir(parents=True, exist_ok=True)

    def write_text(self, relative_path: str, content: str):
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def read_text(self, relative_path: str) -> Optional[str]:
        path = self.root / relative_path
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        return None

    def write_json(self, relative_path: str, data: Any):
        content = json.dumps(data, indent=2, ensure_ascii=False)
        self.write_text(relative_path, content)

    def read_json(self, relative_path: str) -> Optional[Any]:
        content = self.read_text(relative_path)
        if content:
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return None
        return None

    def exists(self, relative_path: str) -> bool:
        return (self.root / relative_path).exists()
