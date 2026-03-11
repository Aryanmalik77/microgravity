"""
AgenticPlanner - Step-by-step agentic UI automation with dynamic Gemini feedback.

Instead of planning all steps upfront, this planner operates in a true
observe → decide → act → verify loop where Gemini sees the screen after
every step and dynamically decides what to do next.
"""

import os
import json
import time
from typing import Dict, Any, Optional, List
from PIL import Image
from google import genai
from google.genai import types


class AgenticPlanner:
    """
    Replaces the static GoalManager with a step-by-step agentic loop.
    
    Each iteration:
      1. OBSERVE: Capture current screen state
      2. DECIDE: Send screenshot + context to Gemini → get ONE next action
      3. ACT: Execute that action (done by UIAgent)
      4. VERIFY: Capture after-state, send verification prompt
      5. RECORD: Update step history with result
      6. LOOP: If goal not complete, repeat
    """

    # Dynamic prompt that steers Gemini to think step-by-step
    SYSTEM_PROMPT = """You are an autonomous UI automation agent controlling a Windows desktop.
You can see the screen and must decide the SINGLE NEXT ACTION to perform.

Available actions:
- {"action": "click", "target": "<description>", "hint_coords": [y_center_norm, x_center_norm], "needs_zoom": false}
- {"action": "double_click", "target": "<description>", "hint_coords": [y_norm, x_norm]}
- {"action": "type", "text": "<text to type>"}
- {"action": "press", "key": "<key name like enter, tab, escape, f5>"}
- {"action": "hotkey", "keys": ["ctrl", "t"]}  # e.g. New Tab
- {"action": "hotkey", "keys": ["ctrl", "w"]}  # e.g. Close Tab
- {"action": "hotkey", "keys": ["ctrl", "tab"]} # e.g. Switch Tab
- {"action": "scroll", "direction": "up|down", "amount": 300}
- {"action": "focus_window", "hwnd": <HWND_INT>} # Directly restores and focuses a window using its handle. Use this for reliable switching, especially if multiple instances are open.
- {"action": "request_closeup_zoom", "target": "<description of tiny element>"} # PROACTIVELY use to calculate precise coordinates for tiny targets like tabs or close buttons, especially if standard clicks failed.
- {"action": "delegate_to_browser_tool", "objective": "<description of what the browser tool should do>"} # Use this ONLY for deep web extraction, complex DOM navigation, or headless interactions that are better suited for Stagehand/PinchTab.
- {"action": "wait", "duration": 1.5, "reason": "<why waiting>"}

### CV Analysis Tools (use these to inspect UI elements before acting):
- {"action": "cv_template_match", "target_label": "<element name>", "threshold": 0.80}  # Searches for a known element template on screen. Returns {matched, coords, confidence}.
- {"action": "cv_snip_element", "element_label": "<name>", "bbox": [x,y,w,h]}  # Crops and saves the element for future matching.
- {"action": "cv_fingerprint_compare", "element_label": "<name>"}  # Checks if element changed state (hover, active, disabled).
- {"action": "cv_stability_check", "region": [x,y,w,h]}  # Checks if a region is STATIC or DYNAMIC.
- {"action": "cv_embedding_search", "target_description": "<what element looks like>"}  # Finds visually similar elements.
- {"action": "request_closeup_zoom", "target": "<description of tiny element>"}  # 2-pass precision zoom for small/overlapping targets.

### Edge Correlation Tools (use for complex UIs or learning new apps):
- {"action": "cv_edge_detect", "annotate": true}  # Runs full edge detection + assigns Correlational IDs (CIDs) to all visible elements. Returns structural map.
- {"action": "cv_structural_map"}  # Returns the positional graph showing how elements relate (left_of, above, inside, etc.) with CIDs.
- {"action": "cv_find_by_cid", "cid": "<CID_xxxxxxxxxxxx>"}  # Locates a specific element by its correlational ID. Use this to re-find UI elements across frames.

### CRITICAL: Element Disambiguation
When multiple elements on screen share the SAME LABEL (e.g., two buttons both labeled "Log In"):
1. **Always specify spatial context** in your target description: e.g. "Log In button inside the login dialog" vs "Log In button on the top navigation bar".
2. **After opening a dialog/modal**, the submit/confirm button is INSIDE the dialog, NOT behind it on the page.
3. **Never reuse coordinates** from an element you interacted with BEFORE a dialog appeared — dialog elements have DIFFERENT coordinates.
4. If a click on a button "opens a dialog" instead of "submitting a form", you clicked the WRONG instance. Look for the button INSIDE the dialog.

### CRITICAL: Modal/Dialog Focus
When a popup, dialog, or overlay is visible on screen:
- ONLY interact with elements INSIDE the dialog/modal.
- Elements behind the dialog are NOT clickable and will cause failures.
- Look for submit buttons, close buttons, and input fields WITHIN the dialog boundary.
- If you need to dismiss the dialog, click its close button or press Escape.

### Tab Management & Multi-Window Philosophy:
1. **In-Place Execution**: If the application needed for the goal is ALREADY OPEN and visible on screen, DO NOT try to open it again. Use the existing window.
2. **Multi-Instance Handling**: If multiple windows of the same app are open, use the `focus_window` action with the specific `hwnd` mentioned in the ENVIRONMENT AWARENESS to select the correct one.
3. **Tab Discovery**: If you need to find something that might be in a different tab, use `ctrl+tab` or click on tab titles to scan all open options. 
4. **Cross-Tab Suggestion**: You should look at tab titles and content to suggest features or options from other tabs if they are relevant to the goal.
5. **Proactive Discovery**: If you see interesting features or options in OTHER tabs or menus while performing your task, mention them in your `reasoning`. You can offer to explore them if they might help the user reach their goal faster.
6. **Tab Lifecycle**: You can open new tabs (`ctrl+t`) or close unnecessary ones (`ctrl+w`) to keep the workspace clean.

Coordinate format: hint_coords are [y, x] normalized to 0-1000 range.
If the target element is SMALL (tabs, icons, small buttons), set "needs_zoom": true.

Your response MUST be a single JSON object with these fields:
{
  "reasoning": "<1-2 sentence explanation of what you see, why this action, and if you are switching tabs/windows>",
  "action": "<action type>",
  "target": "<element description if click>",
  "hint_coords": [y_norm, x_norm],
  "needs_zoom": false,
  "goal_complete": false,
  ... other action-specific fields
}

Set "goal_complete": true ONLY when the original goal has been fully achieved.
If you believe the goal cannot be achieved, set "goal_failed": true with a "failure_reason".
"""

    MAX_STEPS = 30  # Safety limit to prevent infinite loops
    MAX_RETRIES_PER_STEP = 2

    def __init__(self, model_name: str = "models/gemini-2.5-flash", situational_awareness=None,
                 experiential_memory=None, decision_manager=None,
                 presumption_engine=None, outcome_tracker=None):
        from microgravity.config.loader import load_config
        self.model_name = model_name
        config = load_config()
        api_key = config.providers.gemini.api_key
        if not api_key:
            raise ValueError("GEMINI_API_KEY not configured in config.json")
        self.client = genai.Client(api_key=api_key)
        
        self.goal: Optional[str] = None
        self.step_history: List[Dict[str, Any]] = []
        self.current_step: int = 0
        self._is_complete: bool = False
        self._is_failed: bool = False
        self._failure_reason: str = ""
        self.last_action_coords: Optional[Dict[str, Any]] = None
        self.consecutive_failures: int = 0
        self.tab_inventory: Dict[str, str] = {}
        
        # Awareness stack hooks
        self.situational_awareness = situational_awareness  # SituationalAwareness instance
        self.experiential_memory = experiential_memory      # ExperientialMemory instance
        self.decision_manager = decision_manager            # DecisionManager instance
        self.presumptions = presumption_engine              # PresumptionEngine instance
        self.outcomes = outcome_tracker                     # ActionOutcomeTracker instance

    def set_goal(self, goal_description: str):
        """Sets the high-level goal for the agent."""
        self.goal = goal_description
        self.step_history = []
        self.current_step = 0
        self._is_complete = False
        self._is_failed = False
        print(f"[AgenticPlanner] Goal set: {goal_description}")

    def is_complete(self) -> bool:
        """Returns True if the goal is achieved or max steps reached."""
        if self.current_step >= self.MAX_STEPS:
            print(f"[AgenticPlanner] Safety limit reached ({self.MAX_STEPS} steps). Stopping.")
            return True
        return self._is_complete or self._is_failed

    def get_status(self) -> str:
        """Returns a human-readable status string."""
        if self._is_complete:
            return "COMPLETE"
        elif self._is_failed:
            return f"FAILED: {self._failure_reason}"
        else:
            return f"Step {self.current_step}/{self.MAX_STEPS}"

    def _build_dynamic_context(self) -> str:
        """
        Builds a dynamic context prompt that includes:
        - The original goal
        - World Model context (from SituationalAwareness)
        - Experiential memory context (hypotheses, processes, nuances)
        - History of completed steps with success/failure
        - Current step number
        """
        context_parts = [f"## GOAL\n{self.goal}\n"]
        
        # Inject World Model context from SituationalAwareness
        if self.situational_awareness:
            try:
                world_context = self.situational_awareness.get_context_for_planner()
                if world_context:
                    context_parts.append("## ENVIRONMENT AWARENESS")
                    context_parts.append(world_context)
                    
                    # --- NEW: Inject Explicit Bounding Boxes ---
                    model = self.situational_awareness.get_world_model()
                    if model and model.element_map:
                        context_parts.append("\n### Detected Elements (Pixel Coordinates)")
                        for i, el in enumerate(model.element_map):
                            context_parts.append(f"- [{i}] {el['type']} '{el.get('label', '')}': [x: {el['x']}, y: {el['y']}, w: {el['w']}, h: {el['h']}]")
                    
                    context_parts.append("")
            except Exception as e:
                print(f"[AgenticPlanner] World context error: {e}")
        
        # Inject Experiential Memory context
        if self.experiential_memory:
            try:
                # Determine current app class from world model
                app_class = ""
                if self.situational_awareness:
                    m = self.situational_awareness.get_world_model()
                    app_class = m.foreground_state.get("class_name", "")
                
                memory_context = self.experiential_memory.get_context_for_planner(
                    app_class=app_class, current_task=self.goal or ""
                )
                if memory_context:
                    context_parts.append("## LEARNED KNOWLEDGE")
                    context_parts.append(memory_context)
                    context_parts.append("")
            except Exception as e:
                print(f"[AgenticPlanner] Memory context error: {e}")

        # Inject Fast Action Candidates (Presumptions)
        app_class = ""
        if self.situational_awareness:
            ctx = self.situational_awareness.get_current_context()
            app_class = ctx.get("app_class", "")

        if self.presumptions and app_class:
            try:
                candidates = self.presumptions.get_fast_action_candidates(app_class, min_weight=0.7)
                if candidates:
                    context_parts.append("## HIGH-CONFIDENCE PRESUMPTIONS (Fast Actions)")
                    context_parts.append("These elements have verified, stable locations. You can target them by label directly:")
                    for c in candidates[:5]:
                        context_parts.append(f"  - '{c['label']}' ({c['type']}) is typically at {c['location']} "
                                             f"(coords: {c['coords'][0]:.2f}, {c['coords'][1]:.2f}) [conf={c['confidence']:.2f}]")
                    context_parts.append("")
            except Exception as e:
                print(f"[AgenticPlanner] Presumption context error: {e}")
        if self.step_history:
            context_parts.append("## COMPLETED STEPS")
            for i, step in enumerate(self.step_history[-8:], 1):  # Last 8 steps for context window
                status = "[OK] SUCCESS" if step.get("success") else "[X] FAILED"
                action_desc = step.get("action_type", "unknown")
                target = step.get("target", "")
                reasoning = step.get("reasoning", "")
                verification = step.get("verification_note", "")
                
                step_line = f"  Step {step['step_num']}: [{status}] {action_desc}"
                if target:
                    step_line += f" on '{target}'"
                if reasoning:
                    step_line += f" -> {reasoning}"
                if verification:
                    step_line += f" | Verify: {verification}"
                context_parts.append(step_line)
            context_parts.append("")
            
        if self.tab_inventory:
            context_parts.append("## TAB INVENTORY (Discovered so far)")
            for tab, summary in self.tab_inventory.items():
                context_parts.append(f"  - {tab}: {summary}")
            context_parts.append("")
        
        context_parts.append(f"## CURRENT STATE")
        context_parts.append(f"Step number: {self.current_step + 1}")
        context_parts.append(f"Look at the CURRENT screenshot and decide the SINGLE NEXT ACTION.")
        
        if self.step_history and not self.step_history[-1].get("success"):
            last_step = self.step_history[-1]
            context_parts.append("\n> [!WARNING] The PREVIOUS step FAILED. Adapt your approach.")
            context_parts.append(f"> Failed action: {last_step.get('action_type')} on '{last_step.get('target', '')}'")
            
            coords = last_step.get("resolved_coords")
            if coords:
                context_parts.append(f"> FAILED at screen coordinates: x={coords.get('x')}, y={coords.get('y')}")
                context_parts.append("> If the target was slightly missed, adjust your hint_coords accordingly.")
            
            # Surface semantic consequence and root cause from the Learning Loop
            fi = last_step.get("failure_info", {})
            if fi.get("consequence_reason"):
                context_parts.append(f"> Consequence Analysis: {fi['consequence_reason']}")
            if fi.get("root_cause"):
                context_parts.append(f"> Root Cause: {fi['root_cause']} — {fi.get('details', '')}")
            
            # Inject history-driven improvement suggestions
            if self.outcomes:
                try:
                    suggs = self.outcomes.get_improvement_suggestions(last_step.get('target', ''), app_class)
                    if suggs:
                        context_parts.append("> EXPERIENTIAL SUGGESTIONS:")
                        for s in suggs:
                            context_parts.append(f">   - {s}")
                except Exception:
                    pass
            
            context_parts.append(f"> Re-examine the screen state and try an alternative approach.\n")
        
        return "\n".join(context_parts)

    def decide_next_step(self, screenshot_path: str) -> Optional[Dict[str, Any]]:
        """
        Core agentic decision function.
        
        Takes a screenshot of the current screen state, builds a dynamic
        context prompt, and queries Gemini for the single next action.
        
        Returns an action dict or None if goal is complete.
        """
        if self.is_complete():
            return None
        
        self.current_step += 1
        print(f"\n[AgenticPlanner] ====== Step {self.current_step} ======")
        
        # Build dynamic context
        context = self._build_dynamic_context()
        
        # Stuck detection: if the same target+action failed recently, alert the agent
        if len(self.step_history) >= 2:
            last = self.step_history[-1]
            prev = self.step_history[-2]
            if (not last["success"] and not prev["success"] and 
                last["action_type"] == prev["action_type"] and 
                last["target"] == prev["target"]):
                print("[AgenticPlanner] STUCK DETECTED: Same action failed twice.")
                context += "\n> [!IMPORTANT] You are STUCK. Trying the same action twice failed. DO NOT try it a third time. Try a different strategy (e.g. click a different part of the icon, wait, or use a keyboard shortcut).\n"
        
        # Enhanced stuck detection: build a blacklist of failed targets with their coordinates
        # This prevents memory prejudice where the agent keeps returning to the same wrong element
        failed_targets_blacklist = []
        for step in self.step_history[-6:]:
            if not step.get("success") and step.get("target"):
                coords = step.get("resolved_coords", {})
                entry = f"'{step['target']}'"
                if coords:
                    entry += f" at approx ({coords.get('x', '?')}, {coords.get('y', '?')})"
                failed_targets_blacklist.append(entry)
        
        if failed_targets_blacklist:
            context += "\n> [!CAUTION] BLACKLISTED TARGETS (recently failed — DO NOT click these again at the same coordinates):\n"
            for t in failed_targets_blacklist:
                context += f">   ✗ {t}\n"
            context += "> If you need to click an element with the same label, it MUST be at DIFFERENT coordinates (e.g. inside a dialog instead of on the page behind it).\n"

        print(f"[AgenticPlanner] Context:\n{context}")
        
        # Load screenshot
        try:
            img = Image.open(screenshot_path)
        except Exception as e:
            print(f"[AgenticPlanner] Failed to load screenshot: {e}")
            return {"action": "wait", "duration": 1.0, "reasoning": "Screenshot capture failed, retrying"}
        
        # Query Gemini with screenshot + dynamic context
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[
                    self.SYSTEM_PROMPT,
                    context,
                    "Current screen state:",
                    img
                ],
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    response_mime_type="application/json"
                )
            )
            
            raw_text = response.text.strip()
            print(f"[AgenticPlanner] Gemini response: {raw_text}")
            
            # Parse the JSON response
            decision = json.loads(raw_text)
            
        except json.JSONDecodeError as e:
            print(f"[AgenticPlanner] JSON parse error: {e}. Raw: {raw_text}")
            # Try to extract JSON from markdown wrappers
            if "```json" in raw_text:
                json_block = raw_text.split("```json")[1].split("```")[0].strip()
                decision = json.loads(json_block)
            else:
                return {"action": "wait", "duration": 1.0, "reasoning": "Failed to parse Gemini response"}
        except Exception as e:
            print(f"[AgenticPlanner] Gemini query failed: {e}")
            return {"action": "wait", "duration": 1.0, "reasoning": f"Gemini API error: {e}"}
        
        # Check for goal completion
        if decision.get("goal_complete"):
            print(f"[AgenticPlanner] [OK] Goal COMPLETE: {decision.get('reasoning', '')}")
            self._is_complete = True
            return None
        
        if decision.get("goal_failed"):
            self._is_failed = True
            self._failure_reason = decision.get("failure_reason", "Unknown")
            print(f"[AgenticPlanner] [X] Goal FAILED: {self._failure_reason}")
            return None
        
        # Log the decision
        print(f"[AgenticPlanner] Decision: {decision.get('action')} — {decision.get('reasoning', '')}")
        
        return decision

    def verify_step(self, action: Dict[str, Any], after_screenshot_path: str) -> bool:
        """
        After executing an action, verify whether it succeeded by
        sending the after-screenshot to Gemini with context.
        
        This is the verification half of the agentic loop.
        """
        target = action.get("target", action.get("text", ""))
        action_type = action.get("action", "unknown")
        reasoning = action.get("reasoning", "")
        
        # Skip verification for wait/press/hotkey (hard to visually verify)
        if action_type in ["wait", "press", "hotkey"]:
            self._record_step(action, success=True, verification_note="Skipped (non-visual action)")
            return True
        
        try:
            img = Image.open(after_screenshot_path)
        except Exception as e:
            print(f"[AgenticPlanner] Failed to load after-screenshot: {e}")
            self._record_step(action, success=True, verification_note="Screenshot unavailable")
            return True
        
        verify_prompt = f"""You are an expert UI verification agent.
You just executed this action:
- Action: {action_type}
- Target: {target}
- INTENDED CONSEQUENCE: {reasoning}

Look at the CURRENT screen state (after the action).
Does it show data/UI changes consistent with the action reaching its target?

CHECK FOR:
1. **Visual Cues**: Did a new window appear? Did a menu open? Did text appear in a box?
2. **State Match**: If clicking an icon, is that app now in the foreground?
3. **Negative Cues**: Did a 'Not Found' or 'Error' popup appear instead?

Respond in JSON ONLY with this structure:
{{
  "observation": "<precise description of what changed on screen>",
  "success": true/false,
  "confidence": 0.0-1.0,
  "analysis": "<detailed technical explanation of why it succeeded or failed based on visual evidence>",
  "discovered_tabs": [{{"title": "Tab Title", "summary": "Brief summary of content"}}],
  "note": "<brief summary for agent history>"
}}
"""
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[verify_prompt, img],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_mime_type="application/json"
                )
            )
            
            result = json.loads(response.text.strip())
            success = result.get("success", True)
            note = result.get("note", result.get("analysis", ""))
            observation = result.get("observation", "")
            
            print(f"[AgenticPlanner] Verification: {'[OK] SUCCESS' if success else '[X] FAILED'} -- {note}")
            
            self._record_step(action, success=success, 
                            verification_note=f"{note} | Screen: {observation}",
                            discovered_tabs=result.get("discovered_tabs", []))
            return success
            
        except Exception as e:
            print(f"[AgenticPlanner] Verification query failed: {e}. Assuming success.")
            self._record_step(action, success=True, verification_note=f"Verification error: {e}")
            return True

    def _record_step(self, action: Dict[str, Any], success: bool, verification_note: str = "", discovered_tabs: List[Dict[str, str]] = None):
        """Records a completed step in the history for context building."""
        step_record = {
            "step_num": self.current_step,
            "action_type": action.get("action", "unknown"),
            "target": action.get("target", action.get("text", "")),
            "reasoning": action.get("reasoning", ""),
            "success": success,
            "verification_note": verification_note,
            "resolved_coords": action.get("resolved_coords"),
            "failure_info": action.get("failure_info", {}),
            "timestamp": time.time()
        }
        self.step_history.append(step_record)
        
        # New: Register tabs
        if discovered_tabs:
            for tab_info in discovered_tabs:
                title = tab_info.get("title")
                if title:
                    self.tab_inventory[title] = tab_info.get("summary", "No summary")
        
        # New: Auto-register tabs if reasoning mention discovery
        reasoning = step_record.get("reasoning", "").lower()
        if "tab" in reasoning or "window" in reasoning:
            # We don't have the exact tab name here, but the LLM will provide it 
            # in the next turn's reasoning after seeing the verified screen.
            pass
            
        if not success:
            self.consecutive_failures += 1
        else:
            self.consecutive_failures = 0

    def get_step_summary(self) -> str:
        """
        Returns a text summary of the last completed step.
        This is sent as a text input to the Live API to steer its understanding.
        """
        if not self.step_history:
            return f"Starting task: {self.goal}"
        
        last = self.step_history[-1]
        status = "SUCCESS" if last["success"] else "FAILED"
        summary = (
            f"Step {last['step_num']} completed: {last['action_type']}"
        )
        if last.get("target"):
            summary += f" on '{last['target']}'"
        summary += f". Result: {status}."
        if last.get("verification_note"):
            summary += f" {last['verification_note']}"
        
        return summary

    def get_full_history_summary(self) -> str:
        """Returns a complete summary of all steps for final reporting."""
        lines = [f"Task: {self.goal}", f"Status: {self.get_status()}", ""]
        for step in self.step_history:
            status = "[OK]" if step["success"] else "[X]"
            lines.append(f"  {status} Step {step['step_num']}: {step['action_type']} on '{step.get('target', '')}'")
            if step.get("reasoning"):
                lines.append(f"    Reason: {step['reasoning']}")
        return "\n".join(lines)
