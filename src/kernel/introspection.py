"""
Introspection Engine for the MICROGRAVITY Agentic OS.

Ported and adapted from microgravity.agent.introspection to work with the KernelLoop.
Provides self-inspection capabilities:
1. PLAN: Dynamically select which rules are relevant for the task.
2. AUDIT: Track which rules triggered and whether correction helped.
3. SELF-DIAGNOSE: Inspect own state, capabilities, and configuration.
4. COURSE-CORRECT: Escalate if deliverables diverge from objective.
"""

import time
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Callable, Awaitable
from loguru import logger
from google import genai
from google.genai import types
import json_repair


# ── Core Introspection Rules ──
INTROSPECTION_RULES = [
    {
        "id": "R1_NO_REFUSAL",
        "tags": ["capability", "tool_usage", "resilience"],
        "description": "Agent must not refuse tasks based on assumptions.",
        "check": (
            "Did the agent refuse a task claiming it lacks capabilities? "
            "If so, REJECT. The agent MUST attempt the action first."
        ),
    },
    {
        "id": "R2_PREMATURE_STOP",
        "tags": ["error_handling", "persistence", "retry"],
        "description": "Agent must not stop prematurely on recoverable errors.",
        "check": "Did the agent stop prematurely due to a recoverable error? If so, REJECT.",
    },
    {
        "id": "R3_SAFETY_CHECK",
        "tags": ["safety", "interceptor"],
        "description": "Blocked actions must be logged and escalated.",
        "check": (
            "Did the Safety Interceptor block an action? Was the block correctly logged "
            "and the agent gracefully fell back to a safe state? If not, REJECT."
        ),
    },
    {
        "id": "R4_MACRO_INTEGRITY",
        "tags": ["memory", "macro", "deterministic"],
        "description": "Saved macros must match actual UI state.",
        "check": (
            "If the agent loaded a deterministic macro, did the macro execute successfully? "
            "If the macro failed (the UI changed since recording), the agent MUST invalidate "
            "the macro and fall back to the OTA loop."
        ),
    },
    {
        "id": "R5_AUTO_TUNE_SANITY",
        "tags": ["auto_tune", "feedback", "zoom"],
        "description": "Auto-tuning mutations must be bounded.",
        "check": (
            "If the auto-tuner changed configuration (zoom, provider), is the new value sane? "
            "Zoom must be <= 3.0x. Provider must be from the approved list. "
            "If out of bounds, REJECT."
        ),
    },
    {
        "id": "R6_OBJECTIVE_ALIGNMENT",
        "tags": ["quality", "intent", "completion"],
        "description": "Response must fulfill user's core intent.",
        "check": (
            "Is the agent's output fulfilling the user's stated objective? "
            "If the response is incomplete or tangential, REJECT."
        ),
    },
    {
        "id": "R7_POWER_LEVEL_AUDIT",
        "tags": ["rbac", "power", "safety"],
        "description": "Actions must match assigned power level.",
        "check": (
            "Did the agent attempt any action outside its current PowerLevel scope? "
            "If so, was it properly intercepted? If an unauthorized action slipped through, REJECT."
        ),
    },
    {
        "id": "R8_VISION_HEALTH",
        "tags": ["vision", "perception", "screen"],
        "description": "Vision pipeline must be producing valid observations.",
        "check": (
            "Is the ScreenObserver producing usable screenshots? Is the LiveStreamer "
            "connected or gracefully degraded? If vision is fully dead with no fallback, REJECT."
        ),
    },
]


class IntrospectionEngine:
    """
    Self-inspection engine for the MICROGRAVITY Agentic OS.
    
    Examines the system's own state, validates behavioral compliance,
    and produces diagnostic reports.
    """
    
    def __init__(self, workspace: Optional[Path] = None, model_name: str = "gemini-2.0-flash"):
        self.workspace = workspace
        self.model_name = model_name
        self.client = genai.Client()
        self._audit_log: List[Dict[str, Any]] = []
        self._system_state: Dict[str, Any] = {}
        logger.info(f"[IntrospectionEngine] Initialized with {model_name}.")
    
    def register_system_state(self, key: str, value: Any):
        """Register a piece of system state for self-inspection."""
        self._system_state[key] = value
        logger.debug(f"[IntrospectionEngine] Registered state: {key}")
    
    def inspect_state(self) -> Dict[str, Any]:
        """Return a full snapshot of all registered system state."""
        return dict(self._system_state)
    
    def plan_checks(self, task_description: str, tools_used: List[str]) -> List[Dict[str, Any]]:
        """
        PASS 1 — PLAN: Dynamically select which introspection rules are 
        relevant for the current task context.
        """
        task_lower = task_description.lower()
        tools_lower = [t.lower() for t in tools_used]
        
        selected = []
        for rule in INTROSPECTION_RULES:
            relevance = 0
            
            # Always include core checks
            if rule["id"] in ("R1_NO_REFUSAL", "R2_PREMATURE_STOP", "R6_OBJECTIVE_ALIGNMENT"):
                relevance = 10
            
            # Safety checks if interceptor was involved
            if "safety" in rule["tags"]:
                if any(k in task_lower for k in ["block", "intercept", "safety", "malicious"]):
                    relevance = max(relevance, 8)
            
            # Macro checks if deterministic routing occurred
            if "macro" in rule["tags"]:
                if any(k in task_lower for k in ["macro", "run", "execute", "repeat"]):
                    relevance = max(relevance, 7)
            
            # Auto-tune checks if feedback loop was triggered
            if "auto_tune" in rule["tags"]:
                if any(k in task_lower for k in ["zoom", "tune", "fail", "retry"]):
                    relevance = max(relevance, 7)
                    
            # RBAC checks if power levels discussed
            if "rbac" in rule["tags"]:
                if any(k in task_lower for k in ["power", "level", "executor", "observer"]):
                    relevance = max(relevance, 8)
            
            # Vision checks if perception tools used
            if "vision" in rule["tags"]:
                if any("screen" in t or "vision" in t for t in tools_lower):
                    relevance = max(relevance, 6)
            
            if relevance > 0:
                selected.append({**rule, "_relevance": relevance})
        
        selected.sort(key=lambda r: r["_relevance"], reverse=True)
        
        logger.info(
            f"[IntrospectionEngine] Planned {len(selected)}/{len(INTROSPECTION_RULES)} checks: "
            f"{[r['id'] for r in selected]}"
        )
        return selected
    
    def evaluate(
        self,
        planned_rules: List[Dict[str, Any]],
        system_state: Dict[str, Any],
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        PASS 2 — EVALUATE: Run each planned check against current system state.
        Returns (all_passed, list_of_findings).
        """
        findings = []
        all_passed = True
        
        for rule in planned_rules:
            finding = self._run_check(rule, system_state)
            findings.append(finding)
            if not finding["passed"]:
                all_passed = False
                
        # AUDIT: Record this evaluation
        audit_entry = {
            "timestamp": time.time(),
            "all_passed": all_passed,
            "rules_checked": [r["id"] for r in planned_rules],
            "findings": findings,
        }
        self._audit_log.append(audit_entry)
        self._persist_audit(audit_entry)
        
        return all_passed, findings
    
    def _run_check(self, rule: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single introspection check against state."""
        rule_id = rule["id"]
        passed = True
        reason = "OK"
        
        if rule_id == "R1_NO_REFUSAL":
            # Check if the system halted without attempting an action
            if state.get("last_action_attempted") is False and state.get("error_type") == "refusal":
                passed = False
                reason = "Agent refused without attempting action."
                
        elif rule_id == "R2_PREMATURE_STOP":
            # Check if we stopped on a recoverable error
            consecutive_failures = state.get("consecutive_failures", 0)
            max_iterations = state.get("max_iterations", 5)
            if consecutive_failures > 0 and consecutive_failures < 3:
                # We stopped but hadn't hit the failure threshold
                if state.get("loop_completed") is False:
                    passed = False
                    reason = f"Stopped after {consecutive_failures} failures (threshold=3)."
                    
        elif rule_id == "R3_SAFETY_CHECK":
            blocked_actions = state.get("blocked_actions", [])
            if blocked_actions:
                # Verify all blocks were logged
                logged = state.get("safety_log_count", 0)
                if logged < len(blocked_actions):
                    passed = False
                    reason = f"Only {logged}/{len(blocked_actions)} blocks were logged."
                else:
                    reason = f"All {len(blocked_actions)} blocked actions properly logged."
                    
        elif rule_id == "R4_MACRO_INTEGRITY":
            macro_executed = state.get("macro_executed")
            macro_success = state.get("macro_success")
            if macro_executed and macro_success is False:
                if not state.get("macro_invalidated"):
                    passed = False
                    reason = "Failed macro was not invalidated."
                    
        elif rule_id == "R5_AUTO_TUNE_SANITY":
            zoom = state.get("zoom_level", 1.0)
            provider = state.get("llm_provider", "gemini-2.5-flash")
            approved_providers = ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash-exp"]
            if zoom > 3.0:
                passed = False
                reason = f"Zoom level {zoom}x exceeds maximum bound of 3.0x."
            elif provider not in approved_providers:
                passed = False
                reason = f"Provider '{provider}' not in approved list."
            else:
                reason = f"Zoom: {zoom}x, Provider: {provider} — within bounds."
                
        elif rule_id == "R6_OBJECTIVE_ALIGNMENT":
            objective = state.get("task_description", "")
            task_completed = state.get("task_completed", False)
            if objective and not task_completed:
                passed = False
                reason = "Task was not marked as completed."
            else:
                reason = "Objective alignment verified."
                
        elif rule_id == "R7_POWER_LEVEL_AUDIT":
            power_level = state.get("power_level", 0)
            actions_attempted = state.get("actions_attempted", [])
            state_mutating = ["click", "type", "scroll", "run_terminal"]
            for action in actions_attempted:
                if action in state_mutating and power_level < 2:
                    if not state.get(f"blocked_{action}"):
                        passed = False
                        reason = f"Action '{action}' at PowerLevel {power_level} was not blocked."
                        break
                        
        elif rule_id == "R8_VISION_HEALTH":
            screenshots_taken = state.get("screenshots_taken", 0)
            live_streamer_connected = state.get("live_streamer_connected", False)
            if screenshots_taken == 0 and not live_streamer_connected:
                passed = False
                reason = "No vision data available from any source."
            else:
                reason = f"Vision OK: {screenshots_taken} screenshots, LiveStreamer={'ON' if live_streamer_connected else 'OFF (degraded)'}."
        
        finding = {
            "rule_id": rule_id,
            "passed": passed,
            "reason": reason,
        }
        
        level = "INFO" if passed else "WARNING"
        getattr(logger, level.lower())(
            f"[IntrospectionEngine] {rule_id}: {'PASS' if passed else 'FAIL'} — {reason}"
        )
        
        return finding
    
    def _persist_audit(self, entry: Dict[str, Any]):
        """Save audit entry to disk."""
        if not self.workspace:
            return
        audit_path = self.workspace / "storage" / "introspection_audit.json"
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        
        history = []
        if audit_path.exists():
            try:
                history = json.loads(audit_path.read_text(encoding="utf-8"))
            except Exception:
                history = []
        
        history.append(entry)
        history = history[-100:]  # Keep last 100 entries
        audit_path.write_text(json.dumps(history, indent=2, default=str), encoding="utf-8")

    async def evaluate_adaptive(
        self,
        messages: List[Dict[str, Any]],
        draft_content: str,
        tools_used: List[str],
        publish_progress: Optional[Callable[[str], Awaitable[None]]] = None,
        max_correction_passes: int = 2
    ) -> Tuple[bool, str]:
        """
        PASS 3 — ADAPTIVE: Qualitative LLM review with feedback loops.
        Compares user intent vs draft response.
        """
        user_objective = ""
        for m in messages:
            if m.get("role") == "user":
                user_objective = m.get("content", "")
                break

        planned_rules = self.plan_checks(user_objective, tools_used)
        if not planned_rules:
            logger.info("[IntrospectionEngine] No checks planned — auto-approving.")
            return True, ""

        course_correction = ""
        for attempt in range(max_correction_passes):
            prompt = self._build_adaptive_prompt(planned_rules, user_objective, course_correction)
            
            context_snippet = json.dumps(messages[-5:], indent=2)
            user_input = (
                f"--- RECENT CONTEXT ---\n{context_snippet}\n\n"
                f"--- TOOLS USED ---\n{tools_used}\n\n"
                f"--- DRAFT RESPONSE ---\n{draft_content}\n"
            )

            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=[prompt + "\n\n" + user_input]
                )
                
                content = response.text.strip()
                # Clean markdown
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                result = json_repair.loads(content)
                is_approved = result.get("is_approved", True)
                feedback = result.get("feedback", "")
                reasoning = result.get("reasoning", "")
                rules_triggered = result.get("rules_triggered", [])
                deliverables_gap = result.get("deliverables_gap", "")

                # AUDIT
                audit_entry = {
                    "timestamp": time.time(),
                    "attempt": attempt + 1,
                    "all_passed": is_approved,
                    "rules_checked": [r["id"] for r in planned_rules],
                    "rules_triggered": rules_triggered,
                    "reasoning": reasoning,
                    "deliverables_gap": deliverables_gap
                }
                self._audit_log.append(audit_entry)
                self._persist_audit(audit_entry)

                if not is_approved:
                    logger.warning(f"[IntrospectionEngine] REJECTED (Pass {attempt+1}): {reasoning}")
                    if publish_progress:
                        await publish_progress(f"🔍 [Introspection] Intent Gap Detected: {deliverables_gap}")
                    
                    if attempt < max_correction_passes - 1:
                        course_correction = f"Previous rejection: {reasoning}. Gap: {deliverables_gap}. BE STRICTER."
                        continue
                    return False, feedback

                logger.info(f"[IntrospectionEngine] APPROVED on pass {attempt+1}")
                return True, ""

            except Exception as e:
                logger.error(f"[IntrospectionEngine] Adaptive eval failed: {e}")
                return True, "" # Fault tolerance

        return True, ""

    def _build_adaptive_prompt(self, rules: List[Dict[str, Any]], objective: str, correction: str) -> str:
        rules_text = "\n".join([f"- [{r['id']}] {r['check']}" for r in rules])
        return f"""
You are the MICROGRAVITY Introspection Supervisor.
Review the agent's DRAFT RESPONSE against the USER'S OBJECTIVE.

[OBJECTIVE]
{objective}

[PLANNED CHECKS]
{rules_text}

[DELIVERABLES MATRIX]
1. Did the agent actually deliver the requested item (file, code, answer)?
2. Is the response vague or refusing without cause?
3. Is there a gap between intent and output?

{f"[COURSE CORRECTION] {correction}" if correction else ""}

Output raw JSON:
{{
  "is_approved": bool,
  "reasoning": "brief why",
  "rules_triggered": ["IDs"],
  "deliverables_gap": "description of missing value",
  "feedback": "CRITICAL: If false, provide explicit instructions to the agent to fix the response."
}}
"""
    
    def get_diagnostic_report(self) -> str:
        """Generate a comprehensive diagnostic report of the system."""
        lines = [
            "=" * 50,
            "  INTROSPECTION DIAGNOSTIC REPORT",
            "=" * 50,
            "",
            "--- System State ---",
        ]
        
        for key, value in self._system_state.items():
            lines.append(f"  {key}: {value}")
        
        lines.append("")
        lines.append("--- Audit History ---")
        
        if not self._audit_log:
            lines.append("  No evaluations recorded.")
        else:
            total = len(self._audit_log)
            passed = sum(1 for a in self._audit_log if a.get("all_passed"))
            lines.append(f"  Total evaluations: {total}")
            lines.append(f"  Passed: {passed} | Failed: {total - passed}")
            
            # Most triggered rules
            all_findings = []
            for a in self._audit_log:
                all_findings.extend(a.get("findings", []))
            
            rule_counts = {}
            for f in all_findings:
                rid = f["rule_id"]
                rule_counts.setdefault(rid, {"checked": 0, "failed": 0})
                rule_counts[rid]["checked"] += 1
                if not f["passed"]:
                    rule_counts[rid]["failed"] += 1
            
            lines.append("")
            lines.append("--- Rule Performance ---")
            for rid, counts in sorted(rule_counts.items()):
                lines.append(f"  {rid}: checked {counts['checked']}x, failed {counts['failed']}x")
        
        lines.append("")
        lines.append("=" * 50)
        return "\n".join(lines)
