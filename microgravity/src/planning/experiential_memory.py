"""
ExperientialMemory — 4-tier hierarchical learning system persisted across sessions.

Hierarchy:
  global/               → Cross-app universal knowledge
  app_classes/           → Per-app-type knowledge (BROWSER, EDITOR, CHAT, etc.)
  app_instances/         → Per-app knowledge (Chrome, VSCode, Notepad)
    └─ site_specific/    → Per-website / per-project knowledge (auto-expanding)

Tiers (at each hierarchy level):
  1. EpisodicMemory: Records full execution episodes (what happened)
  2. HypothesisMemory: Builds testable if-then hypotheses (why things happen)
  3. ProcessMemory: Stores proven reusable action sequences
  4. NuanceLedger: Records subtle edge cases and quirks
"""

import json
import time
import os
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict


# ──────────────────────────  Data Structures  ──────────────────────────

@dataclass
class Episode:
    """A single recorded execution episode."""
    episode_id: str
    task: str
    app_name: str
    app_class: str
    steps: List[Dict[str, Any]]     # [{action, target, result, timestamp, screenshot_hash}]
    success: bool
    failure_reason: str = ""
    duration_s: float = 0.0
    timestamp: float = 0.0
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Hypothesis:
    """A testable if-then hypothesis about UI behavior."""
    hypothesis_id: str
    condition: str                  # "Clicking 'Save' when file is new"
    prediction: str                 # "Opens 'Save As' dialog"
    app_class: str
    evidence_for: int = 0
    evidence_against: int = 0
    confidence: float = 0.0        # evidence_for / (evidence_for + evidence_against + 1)
    is_fact: bool = False           # Promoted when confidence > 0.9 after 5+ tests
    created: float = 0.0
    last_tested: float = 0.0


@dataclass
class ProcessIP:
    """A reusable action sequence (Interaction Pattern)."""
    process_id: str
    task_pattern: str               # "open_file_in_browser", "save_document", etc.
    app_class: str
    steps: List[Dict[str, Any]]     # [{action, target_desc, method}]
    run_count: int = 0
    success_count: int = 0
    category: str = "RARE"          # TYPICAL (>5 runs), SPECIAL (2-5), GENERAL (cross-app), RARE (1)
    created: float = 0.0
    last_used: float = 0.0


@dataclass
class Nuance:
    """A subtle non-obvious behavior record."""
    nuance_id: str
    app_class: str
    element_id: str
    nuance_type: str                # TIMING | MODAL | STATE_DEPENDENT | MULTI_STEP | PLATFORM_QUIRK | RESOURCE
    severity: str                   # CRITICAL | IMPORTANT | INFORMATIONAL
    description: str
    workaround: str = ""
    trigger_condition: str = ""
    created: float = 0.0
    occurrence_count: int = 1


# ──────────────────────────  ExperientialMemory  ──────────────────────────

class ExperientialMemory:
    """4-tier hierarchical learning system persisted to disk.
    
    Hierarchy: global → app_class → app_instance → site/context.
    Every app, website, or context auto-creates its own branch.
    """

    def __init__(self, storage_dir: str = "experiential_memory"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

        # ── Flat stores (backward-compatible) ──
        self.episodes: List[Episode] = []
        self.hypotheses: Dict[str, Hypothesis] = {}
        self.processes: Dict[str, ProcessIP] = {}
        self.nuances: Dict[str, Nuance] = {}

        # ── Hierarchical tree ──
        # Structure: {level: {scope_key: {tier: [items]}}}
        # level = "global" | "app_class" | "app_instance" | "site"
        # scope_key = "*" for global, "BROWSER" for app_class, "Chrome" for instance, "reddit.com" for site
        self._hierarchy: Dict[str, Dict[str, Dict[str, list]]] = {
            "global": {"*": {"hypotheses": [], "processes": [], "nuances": []}},
            "app_class": {},
            "app_instance": {},
            "site": {},
        }

        # ── Indices ──
        self._app_episodes: Dict[str, List[int]] = defaultdict(list)
        self._task_processes: Dict[str, List[str]] = defaultdict(list)

        # ── Cross-app promotion tracking ──
        # hypothesis_id → set of app_classes where it was confirmed
        self._cross_app_confirmations: Dict[str, set] = defaultdict(set)
        self._promotion_threshold = 3  # Promote to global after confirmed in N apps

        # Load persisted data
        self._load()
        print(f"[ExperientialMemory] Loaded: {len(self.episodes)} episodes, {len(self.hypotheses)} hypotheses, "
              f"{len(self.processes)} processes, {len(self.nuances)} nuances")
        print(f"[ExperientialMemory] Hierarchy: "
              f"{len(self._hierarchy['app_class'])} app classes, "
              f"{len(self._hierarchy['app_instance'])} app instances, "
              f"{len(self._hierarchy['site'])} sites")

    # ═══════════════════════  Tier 1: Episodic Memory  ═══════════════════════

    def record_episode(self, task: str, app_name: str, app_class: str,
                       steps: List[Dict], success: bool, failure_reason: str = "",
                       context: Dict = None) -> str:
        """Records a full execution episode."""
        episode_id = f"ep_{int(time.time())}_{len(self.episodes)}"
        ep = Episode(
            episode_id=episode_id,
            task=task,
            app_name=app_name,
            app_class=app_class,
            steps=steps,
            success=success,
            failure_reason=failure_reason,
            duration_s=sum(s.get("duration", 0) for s in steps),
            timestamp=time.time(),
            context=context or {},
        )
        self.episodes.append(ep)
        self._app_episodes[app_class].append(len(self.episodes) - 1)

        # Auto-extract process if successful
        if success and len(steps) >= 2:
            self._maybe_extract_process(ep)

        # Auto-extract nuances from failures
        if not success:
            self._extract_failure_nuance(ep)

        self._save()
        return episode_id

    def recall_similar(self, task: str, app_class: str = "", top_k: int = 3) -> List[Episode]:
        """Retrieves past episodes with similar tasks."""
        task_lower = task.lower()
        scored = []

        for ep in self.episodes:
            # Simple keyword overlap scoring
            ep_words = set(ep.task.lower().split())
            task_words = set(task_lower.split())
            overlap = len(ep_words & task_words)
            score = overlap / max(len(task_words), 1)

            # Boost for same app
            if app_class and ep.app_class == app_class:
                score += 0.3

            # Boost for success
            if ep.success:
                score += 0.2

            if score > 0.2:
                scored.append((score, ep))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [ep for _, ep in scored[:top_k]]

    def get_app_episodes(self, app_class: str) -> List[Episode]:
        """Gets all episodes for a specific app."""
        indices = self._app_episodes.get(app_class, [])
        return [self.episodes[i] for i in indices if i < len(self.episodes)]

    # ═══════════════════════  Tier 2: Hypothesis Memory  ═══════════════════════

    def generate_hypothesis(self, condition: str, prediction: str, app_class: str) -> str:
        """Creates a new hypothesis."""
        hyp_id = f"hyp_{int(time.time())}_{len(self.hypotheses)}"
        self.hypotheses[hyp_id] = Hypothesis(
            hypothesis_id=hyp_id,
            condition=condition,
            prediction=prediction,
            app_class=app_class,
            created=time.time(),
        )
        self._save()
        return hyp_id

    def test_hypothesis(self, hypothesis_id: str, outcome_matches: bool) -> Optional[Hypothesis]:
        """Updates hypothesis confidence based on test result."""
        hyp = self.hypotheses.get(hypothesis_id)
        if not hyp:
            return None

        if outcome_matches:
            hyp.evidence_for += 1
        else:
            hyp.evidence_against += 1

        hyp.confidence = hyp.evidence_for / (hyp.evidence_for + hyp.evidence_against + 1)
        hyp.last_tested = time.time()

        # Promote to fact if confidence is high enough
        total_tests = hyp.evidence_for + hyp.evidence_against
        if hyp.confidence > 0.9 and total_tests >= 5:
            hyp.is_fact = True

        self._save()
        return hyp

    def get_relevant_hypotheses(self, app_class: str, context: str = "") -> List[Hypothesis]:
        """Gets hypotheses relevant to the current app and context."""
        relevant = []
        context_lower = context.lower()

        for hyp in self.hypotheses.values():
            if hyp.app_class == app_class or hyp.app_class == "*":
                # Check if context matches condition
                if not context_lower or any(w in hyp.condition.lower() for w in context_lower.split()):
                    relevant.append(hyp)

        # Sort by confidence descending
        relevant.sort(key=lambda h: h.confidence, reverse=True)
        return relevant[:10]

    # ═══════════════════════  Tier 3: Process Memory  ═══════════════════════

    def find_matching_process(self, task: str, app_class: str = "") -> Optional[ProcessIP]:
        """Finds a stored process matching the current task."""
        task_lower = task.lower()
        best_match = None
        best_score = 0

        for proc in self.processes.values():
            # Keyword overlap
            proc_words = set(proc.task_pattern.lower().split("_"))
            task_words = set(task_lower.split())
            overlap = len(proc_words & task_words)
            score = overlap / max(len(proc_words), 1)

            # Boost same app
            if app_class and proc.app_class == app_class:
                score += 0.4

            # Boost proven processes
            if proc.category == "TYPICAL":
                score += 0.3
            elif proc.category == "GENERAL":
                score += 0.2

            if score > best_score and score > 0.3:
                best_score = score
                best_match = proc

        return best_match

    def record_process(self, task_pattern: str, app_class: str, steps: List[Dict]) -> str:
        """Records a new reusable process."""
        proc_id = f"proc_{int(time.time())}_{len(self.processes)}"
        proc = ProcessIP(
            process_id=proc_id,
            task_pattern=task_pattern,
            app_class=app_class,
            steps=steps,
            run_count=1,
            success_count=1,
            created=time.time(),
            last_used=time.time(),
        )
        self.processes[proc_id] = proc
        self._task_processes[task_pattern].append(proc_id)
        self._save()
        return proc_id

    def update_process_usage(self, process_id: str, success: bool):
        """Updates process usage statistics."""
        proc = self.processes.get(process_id)
        if not proc:
            return

        proc.run_count += 1
        if success:
            proc.success_count += 1
        proc.last_used = time.time()

        # Update category
        if proc.run_count > 5:
            proc.category = "TYPICAL"
        elif proc.run_count >= 2:
            proc.category = "SPECIAL"
        else:
            proc.category = "RARE"

        self._save()

    def replay_process(self, process_id: str) -> Optional[List[Dict]]:
        """Returns the steps of a stored process for replay."""
        proc = self.processes.get(process_id)
        return proc.steps if proc else None

    # ═══════════════════════  Tier 4: Nuance Ledger  ═══════════════════════

    def record_nuance(self, app_class: str, element_id: str, nuance_type: str,
                      severity: str, description: str, workaround: str = "",
                      trigger_condition: str = "") -> str:
        """Records a subtle non-obvious behavior."""
        nuance_id = f"nua_{int(time.time())}_{len(self.nuances)}"
        self.nuances[nuance_id] = Nuance(
            nuance_id=nuance_id,
            app_class=app_class,
            element_id=element_id,
            nuance_type=nuance_type,
            severity=severity,
            description=description,
            workaround=workaround,
            trigger_condition=trigger_condition,
            created=time.time(),
        )
        self._save()
        return nuance_id

    def get_nuances(self, app_class: str, element_id: str = "") -> List[Nuance]:
        """Gets nuances for a specific app and optionally a specific element."""
        results = []
        for n in self.nuances.values():
            if n.app_class == app_class:
                if not element_id or n.element_id == element_id:
                    results.append(n)

        # Sort: CRITICAL first, then IMPORTANT, then INFORMATIONAL
        severity_order = {"CRITICAL": 0, "IMPORTANT": 1, "INFORMATIONAL": 2}
        results.sort(key=lambda n: severity_order.get(n.severity, 3))
        return results

    # ═══════════════════════  Auto-extraction  ═══════════════════════

    def _maybe_extract_process(self, episode: Episode):
        """Auto-extracts a reusable process from a successful episode."""
        # Generate a task pattern from the task description
        words = episode.task.lower().split()
        pattern = "_".join(words[:4])  # Simple pattern from first 4 words

        # Check if similar process already exists
        existing = self.find_matching_process(episode.task, episode.app_class)
        if existing:
            self.update_process_usage(existing.process_id, True)
        else:
            # Extract step summaries
            step_summaries = []
            for s in episode.steps:
                step_summaries.append({
                    "action": s.get("action", ""),
                    "target_desc": s.get("target", ""),
                    "method": s.get("method", ""),
                })
            if step_summaries:
                self.record_process(pattern, episode.app_class, step_summaries)

    def _extract_failure_nuance(self, episode: Episode):
        """Auto-extracts nuances from a failed episode."""
        if not episode.failure_reason:
            return

        reason = episode.failure_reason.lower()

        # Classify nuance type
        if "timeout" in reason or "slow" in reason or "wait" in reason:
            ntype = "TIMING"
        elif "dialog" in reason or "popup" in reason or "modal" in reason:
            ntype = "MODAL"
        elif "state" in reason or "condition" in reason:
            ntype = "STATE_DEPENDENT"
        elif "step" in reason or "sequence" in reason:
            ntype = "MULTI_STEP"
        else:
            ntype = "PLATFORM_QUIRK"

        self.record_nuance(
            app_class=episode.app_class,
            element_id=episode.steps[-1].get("target", "") if episode.steps else "",
            nuance_type=ntype,
            severity="IMPORTANT",
            description=episode.failure_reason,
            trigger_condition=episode.task,
        )

    # ═══════════════════════  Persistence  ═══════════════════════

    def _save(self):
        """Persists all memory to disk (flat + hierarchical)."""
        data = {
            "episodes": [asdict(ep) for ep in self.episodes[-100:]],  # Keep last 100
            "hypotheses": {k: asdict(v) for k, v in self.hypotheses.items()},
            "processes": {k: asdict(v) for k, v in self.processes.items()},
            "nuances": {k: asdict(v) for k, v in self.nuances.items()},
            "hierarchy": self._hierarchy,
            "cross_app_confirmations": {k: list(v) for k, v in self._cross_app_confirmations.items()},
        }

        path = os.path.join(self.storage_dir, "memory.json")
        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            print(f"[ExperientialMemory] Save failed: {e}")

    def _load(self):
        """Loads persisted memory from disk (flat + hierarchical)."""
        path = os.path.join(self.storage_dir, "memory.json")
        if not os.path.exists(path):
            return

        try:
            with open(path, "r") as f:
                data = json.load(f)

            # Restore episodes
            for ep_data in data.get("episodes", []):
                self.episodes.append(Episode(**ep_data))
            for i, ep in enumerate(self.episodes):
                self._app_episodes[ep.app_class].append(i)

            # Restore hypotheses
            for k, v in data.get("hypotheses", {}).items():
                self.hypotheses[k] = Hypothesis(**v)

            # Restore processes
            for k, v in data.get("processes", {}).items():
                self.processes[k] = ProcessIP(**v)
                self._task_processes[v.get("task_pattern", "")].append(k)

            # Restore nuances
            for k, v in data.get("nuances", {}).items():
                self.nuances[k] = Nuance(**v)

            # Restore hierarchy (if exists)
            if "hierarchy" in data:
                self._hierarchy = data["hierarchy"]
            else:
                # Auto-migrate from flat to hierarchical
                self._migrate_flat_to_hierarchy()

            # Restore cross-app confirmations
            for k, v in data.get("cross_app_confirmations", {}).items():
                self._cross_app_confirmations[k] = set(v)

        except Exception as e:
            print(f"[ExperientialMemory] Load failed: {e}")

    def _migrate_flat_to_hierarchy(self):
        """Auto-migrates existing flat data into the hierarchy on first load."""
        print("[ExperientialMemory] Migrating flat data to hierarchical structure...")

        for hyp_id, hyp in self.hypotheses.items():
            ac = hyp.app_class if hyp.app_class != "*" else "*"
            if ac == "*":
                self._hierarchy["global"]["*"]["hypotheses"].append(hyp_id)
            else:
                self._ensure_hierarchy_branch("app_class", ac)
                self._hierarchy["app_class"][ac]["hypotheses"].append(hyp_id)

        for proc_id, proc in self.processes.items():
            ac = proc.app_class
            self._ensure_hierarchy_branch("app_class", ac)
            self._hierarchy["app_class"][ac]["processes"].append(proc_id)

        for nua_id, nua in self.nuances.items():
            ac = nua.app_class
            self._ensure_hierarchy_branch("app_class", ac)
            self._hierarchy["app_class"][ac]["nuances"].append(nua_id)

        # Categorize episodes
        for ep in self.episodes:
            self._categorize_episode(ep)

        self._save()
        print("[ExperientialMemory] Migration complete.")

    # ═══════════════════════  Context Generation  ═══════════════════════

    def get_context_for_planner(self, app_class: str, current_task: str = "",
                                app_instance: str = "", site: str = "") -> str:
        """Generates a concise context string for the planner using hierarchical recall."""
        lines = []

        # Hierarchical hypotheses (specific → general)
        hyps = self.recall_hypotheses_hierarchical(app_class, app_instance, site)
        if hyps:
            lines.append("Known behaviors:")
            for h, source in hyps[:5]:
                status = "FACT" if h.is_fact else f"conf={h.confidence:.1f}"
                lines.append(f"  - IF {h.condition} THEN {h.prediction} [{status}] (from:{source})")

        # Hierarchical process match
        proc, proc_source = self.find_process_hierarchical(current_task, app_class, app_instance)
        if proc:
            lines.append(f"Reusable process: '{proc.task_pattern}' ({proc.category}, {proc.run_count} runs, from:{proc_source})")

        # Nuances (include critical from any level)
        nuances = self.get_nuances(app_class)
        critical_nuances = [n for n in nuances if n.severity == "CRITICAL"]
        if critical_nuances:
            lines.append("⚠ Critical nuances:")
            for n in critical_nuances[:3]:
                lines.append(f"  - [{n.nuance_type}] {n.description[:80]}")

        return "\n".join(lines) if lines else ""

    # ═══════════════════════  Hierarchical Methods  ═══════════════════════

    def _ensure_hierarchy_branch(self, level: str, scope_key: str):
        """Auto-creates a hierarchy branch if it doesn't exist."""
        if scope_key not in self._hierarchy[level]:
            self._hierarchy[level][scope_key] = {
                "hypotheses": [], "processes": [], "nuances": [],
            }
            print(f"[ExperientialMemory] Auto-created hierarchy: {level}/{scope_key}")

    def _extract_site(self, context: Dict) -> str:
        """Extracts a site/context identifier from episode context."""
        # Try URL first
        url = context.get("url", context.get("current_url", ""))
        if url:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(url)
                return parsed.netloc or parsed.path.split("/")[0]
            except Exception:
                pass
        # Try window title
        title = context.get("window_title", context.get("title", ""))
        if title:
            # Extract domain-like patterns from titles
            for pattern in ["- Google Chrome", "- Firefox", "- Microsoft Edge"]:
                if pattern in title:
                    page_title = title.replace(pattern, "").strip()
                    return page_title[:40]  # First 40 chars as context key
        # Try project/file context
        project = context.get("project", context.get("file_path", ""))
        if project:
            return os.path.basename(project)
        return ""

    def _categorize_episode(self, episode: Episode):
        """Sorts episode knowledge into the correct hierarchy branches."""
        app_class = episode.app_class
        app_name = episode.app_name
        site = self._extract_site(episode.context)

        # Ensure branches exist
        self._ensure_hierarchy_branch("app_class", app_class)
        self._ensure_hierarchy_branch("app_instance", app_name)
        if site:
            site_key = f"{app_name}/{site}"
            self._ensure_hierarchy_branch("site", site_key)

    def recall_hypotheses_hierarchical(self, app_class: str, app_instance: str = "",
                                        site: str = "") -> List[Tuple[Hypothesis, str]]:
        """Retrieves hypotheses from specific → general.
        Returns [(hypothesis, source_level)] with specificity weighting."""
        results = []

        # 1. Site-specific
        if site and app_instance:
            site_key = f"{app_instance}/{site}"
            for hyp_id in self._hierarchy.get("site", {}).get(site_key, {}).get("hypotheses", []):
                if hyp_id in self.hypotheses:
                    results.append((self.hypotheses[hyp_id], f"site:{site}"))

        # 2. App-instance
        if app_instance:
            for hyp_id in self._hierarchy.get("app_instance", {}).get(app_instance, {}).get("hypotheses", []):
                if hyp_id in self.hypotheses and (self.hypotheses[hyp_id], f"instance:{app_instance}") not in results:
                    results.append((self.hypotheses[hyp_id], f"instance:{app_instance}"))

        # 3. App-class
        for hyp_id in self._hierarchy.get("app_class", {}).get(app_class, {}).get("hypotheses", []):
            if hyp_id in self.hypotheses:
                results.append((self.hypotheses[hyp_id], f"class:{app_class}"))

        # 4. Global
        for hyp_id in self._hierarchy.get("global", {}).get("*", {}).get("hypotheses", []):
            if hyp_id in self.hypotheses:
                results.append((self.hypotheses[hyp_id], "global"))

        # Deduplicate, sort by confidence
        seen = set()
        deduped = []
        for h, src in results:
            if h.hypothesis_id not in seen:
                seen.add(h.hypothesis_id)
                deduped.append((h, src))
        deduped.sort(key=lambda x: x[0].confidence, reverse=True)
        return deduped

    def find_process_hierarchical(self, task: str, app_class: str,
                                   app_instance: str = "") -> Tuple[Optional[ProcessIP], str]:
        """Searches: site → instance → class → global.
        Returns (process, source_level) or (None, "")."""

        # 1. App-instance processes
        if app_instance:
            for proc_id in self._hierarchy.get("app_instance", {}).get(app_instance, {}).get("processes", []):
                proc = self.processes.get(proc_id)
                if proc and self._task_matches_process(task, proc):
                    return proc, f"instance:{app_instance}"

        # 2. App-class processes
        for proc_id in self._hierarchy.get("app_class", {}).get(app_class, {}).get("processes", []):
            proc = self.processes.get(proc_id)
            if proc and self._task_matches_process(task, proc):
                return proc, f"class:{app_class}"

        # 3. Global processes
        for proc_id in self._hierarchy.get("global", {}).get("*", {}).get("processes", []):
            proc = self.processes.get(proc_id)
            if proc and self._task_matches_process(task, proc):
                return proc, "global"

        # 4. Fallback to flat search
        proc = self.find_matching_process(task, app_class)
        return (proc, "flat") if proc else (None, "")

    def _task_matches_process(self, task: str, proc: ProcessIP) -> bool:
        """Checks if a task description matches a stored process."""
        proc_words = set(proc.task_pattern.lower().replace("_", " ").split())
        task_words = set(task.lower().split())
        overlap = len(proc_words & task_words)
        return overlap / max(len(proc_words), 1) > 0.3

    # ═══════════════════════  Cross-App Generalization  ═══════════════════════

    def promote_to_global(self, hypothesis_id: str):
        """Promotes an app-specific hypothesis to global if confirmed across 3+ apps."""
        hyp = self.hypotheses.get(hypothesis_id)
        if not hyp:
            return

        # Add to global hypotheses
        global_hyps = self._hierarchy["global"]["*"]["hypotheses"]
        if hypothesis_id not in global_hyps:
            global_hyps.append(hypothesis_id)
            hyp.app_class = "*"  # Mark as universal
            print(f"[ExperientialMemory] PROMOTED to global: '{hyp.condition}' -> '{hyp.prediction}'")
            self._save()

    def check_cross_app_promotion(self, hypothesis_id: str, app_class: str):
        """Records that a hypothesis was confirmed in an app and promotes if threshold met."""
        self._cross_app_confirmations[hypothesis_id].add(app_class)
        if len(self._cross_app_confirmations[hypothesis_id]) >= self._promotion_threshold:
            self.promote_to_global(hypothesis_id)

    def extract_cross_app_patterns(self):
        """Scans all app-class knowledge for common patterns and auto-promotes."""
        # Find hypotheses that appear in multiple app classes
        condition_map: Dict[str, List[str]] = defaultdict(list)  # condition → [hyp_ids]
        for hyp_id, hyp in self.hypotheses.items():
            if hyp.app_class != "*":  # Skip already-global
                key = hyp.condition.lower().strip()
                condition_map[key].append(hyp_id)

        promoted = 0
        for condition, hyp_ids in condition_map.items():
            apps = set(self.hypotheses[hid].app_class for hid in hyp_ids if hid in self.hypotheses)
            if len(apps) >= self._promotion_threshold:
                # Promote the highest-confidence one
                best_id = max(hyp_ids, key=lambda hid: self.hypotheses.get(hid, Hypothesis("","","","")).confidence)
                self.promote_to_global(best_id)
                promoted += 1

        if promoted:
            print(f"[ExperientialMemory] Cross-app scan: promoted {promoted} hypotheses to global")

    # ═══════════════════════  Hierarchical Episode Recording  ═══════════════════════

    def record_episode_hierarchical(self, task: str, app_name: str, app_class: str,
                                     steps: List[Dict], success: bool, failure_reason: str = "",
                                     context: Dict = None) -> str:
        """Records an episode with automatic hierarchical categorization."""
        # Use the existing flat recorder
        ep_id = self.record_episode(task, app_name, app_class, steps, success,
                                     failure_reason, context)

        # Categorize into hierarchy
        ep = self.episodes[-1]
        self._categorize_episode(ep)

        # If episode generated hypotheses, file them hierarchically
        site = self._extract_site(context or {})
        if site:
            site_key = f"{app_name}/{site}"
            self._ensure_hierarchy_branch("site", site_key)

        return ep_id

    # ═══════════════════════  Learning Stats  ═══════════════════════

    def get_learning_stats(self) -> Dict[str, Any]:
        """Returns comprehensive learning statistics."""
        # Hypothesis tiers
        facts = [h for h in self.hypotheses.values() if h.is_fact]
        strong = [h for h in self.hypotheses.values() if h.confidence > 0.7 and not h.is_fact]
        weak = [h for h in self.hypotheses.values() if h.confidence <= 0.7]

        # Process categories
        proc_cats = defaultdict(int)
        for p in self.processes.values():
            proc_cats[p.category] += 1

        # Nuance severities
        nua_sev = defaultdict(int)
        for n in self.nuances.values():
            nua_sev[n.severity] += 1

        return {
            "total_episodes": len(self.episodes),
            "successful_episodes": sum(1 for e in self.episodes if e.success),
            "hypotheses": {
                "total": len(self.hypotheses),
                "facts": len(facts),
                "strong": len(strong),
                "weak": len(weak),
            },
            "processes": dict(proc_cats),
            "nuances": dict(nua_sev),
            "hierarchy": {
                "app_classes": list(self._hierarchy["app_class"].keys()),
                "app_instances": list(self._hierarchy["app_instance"].keys()),
                "sites": list(self._hierarchy["site"].keys()),
                "global_hypotheses": len(self._hierarchy["global"]["*"]["hypotheses"]),
                "global_processes": len(self._hierarchy["global"]["*"]["processes"]),
            },
            "cross_app_promotions": sum(
                1 for hyps in self._cross_app_confirmations.values()
                if len(hyps) >= self._promotion_threshold
            ),
        }
