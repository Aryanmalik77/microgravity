import os
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np

import lmdb
from loguru import logger
from src.memory.store import PersistentStore
from src.memory.profile_store import UIProfileStore

class MemoryKernel:
    """
    The central intelligence hub for memory. 
    Unifies Spatial (UI Atlas), Semantic (Vector), Episodic (Execution) knowledge,
    and Procedural Profiles (Macros).
    """
    def __init__(self, storage_root: Path):
        self.storage = PersistentStore(storage_root)
        self.profiles = UIProfileStore(self.storage)
        
        self.atlas_path = "memory/atlas/ui_atlas.json"
        self.screenshots_dir = storage_root / "screenshots"
        self.templates_dir = storage_root / "memory" / "atlas" / "templates"
        
        # Ensure subdirs
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        
        # LMDB Semantic Store
        self.lmdb_path = storage_root / "memory" / "semantic" / "lmdb_store"
        self.lmdb_path.parent.mkdir(parents=True, exist_ok=True)
        self.env = lmdb.open(str(self.lmdb_path), map_size=10485760, create=True)
        
        self.atlas = self._load_atlas()

    def _load_atlas(self) -> Dict[str, Any]:
        data = self.storage.read_json(self.atlas_path)
        if data:
            return data
        return {
            "contexts": {
                "Desktop": {"type": "FIXED", "elements": {}},
                "Taskbar": {"type": "FIXED", "elements": {}}
            },
            "global_elements": {},
            "app_profiles": {},
            "learned_chrome_boundaries": {},
            "version": "4.0"
        }

    def save_atlas(self):
        self.storage.write_json(self.atlas_path, self.atlas)

    def clear_context(self, context: str, permanent_only: bool = False):
        """Clears elements from a context, optionally preserving permanent ones."""
        if context not in self.atlas["contexts"]:
            return
            
        if not permanent_only:
            self.atlas["contexts"][context]["elements"] = {}
        else:
            elements = self.atlas["contexts"][context]["elements"]
            self.atlas["contexts"][context]["elements"] = {
                k: v for k, v in elements.items() if v.get("is_permanent")
            }
        self.save_atlas()
        logger.debug(f"[MemoryKernel] Cleared context '{context}' (permanent_only={permanent_only})")

    # --- Spatial Memory (UI Atlas) ---

    def remember_element(self, context: str, label: str, data: Dict[str, Any], template: Optional[Any] = None):
        """Stores a UI element in the spatial atlas."""
        if context not in self.atlas["contexts"]:
            self.atlas["contexts"][context] = {"elements": {}, "type": "DYNAMIC"}
        
        element_key = label.lower()
        is_permanent = data.get("is_permanent", False)
        
        self.atlas["contexts"][context]["elements"][element_key] = {
            "coords": data.get("coords"),
            "type": data.get("type", "unknown"),
            "is_invariant": data.get("is_invariant", False),
            "is_permanent": is_permanent,
            "last_verified": time.time()
        }
        
        if template is not None:
            # Handle CV2 template saving if passed as numpy array
            import cv2
            template_filename = f"{context}_{element_key}.png"
            template_path = self.templates_dir / template_filename
            cv2.imwrite(str(template_path), template)
            self.atlas["contexts"][context]["elements"][element_key]["template_relative_path"] = f"templates/{template_filename}"
            
        self.save_atlas()

    def recall_element(self, context: str, label: str) -> Optional[Dict[str, Any]]:
        element_key = label.lower()
        if context in self.atlas["contexts"]:
            elements = self.atlas["contexts"][context]["elements"]
            if element_key in elements:
                return elements[element_key]
        return self.atlas["global_elements"].get(element_key)

    # --- Semantic Memory (LMDB + Vector Stub) ---

    def write_text(self, key: str, content: str) -> None:
        """Writes raw text to the LMDB semantic store."""
        with self.env.begin(write=True) as txn:
            txn.put(key.encode("utf-8"), content.encode("utf-8"))

    def read_text(self, key: str) -> Optional[str]:
        """Reads raw text from the LMDB semantic store."""
        with self.env.begin() as txn:
            val = txn.get(key.encode("utf-8"))
            if val is not None:
                return val.decode("utf-8")
        return None

    def append_history(self, entry: str, metadata: Optional[Dict[str, Any]] = None):
        """Appends a structured, timestamped entry to the episodic history."""
        record = {
            "timestamp": time.time(),
            "datetime": time.strftime('%Y-%m-%d %H:%M:%S'),
            "content": entry,
            "tags": metadata.get("tags", []) if metadata else []
        }
        if metadata:
            record.update({k: v for k, v in metadata.items() if k != "tags"})

        with self.env.begin(write=True) as txn:
            k = b"HISTORY_v2"
            val = txn.get(k)
            history = json.loads(val.decode("utf-8")) if val else []
            history.append(record)
            # Keep last 1000 records
            history = history[-1000:]
            txn.put(k, json.dumps(history).encode("utf-8"))

    def search_knowledge(self, query: str, tags: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Searches history and memory with tag filtering and structured results."""
        with self.env.begin() as txn:
            val = txn.get(b"HISTORY_v2")
            if not val:
                 return []
            history = json.loads(val.decode("utf-8"))
            
        q = query.lower()
        results = []
        for entry in history:
            # Match against content text OR tags
            content_match = q in entry.get("content", "").lower()
            tag_match_query = any(q in t.lower() for t in entry.get("tags", []))
            match = content_match or tag_match_query
            
            if tags:
                explicit_tag_match = any(t in entry.get("tags", []) for t in tags)
                if match and explicit_tag_match:
                    results.append(entry)
            elif match:
                results.append(entry)
        return results

    def store_insight(self, insight: str, labels: Optional[List[str]] = None):
        """Stores a long-term insight with labels."""
        record = {
            "timestamp": time.time(),
            "insight": insight,
            "labels": labels or []
        }
        current_val = self.read_text("MEMORY_v2")
        current = json.loads(current_val) if current_val else []
        current.append(record)
        self.write_text("MEMORY_v2", json.dumps(current))
