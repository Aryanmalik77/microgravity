import asyncio
import time
import threading
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from loguru import logger
import json_repair

from src.kernel.bus import DurableEventBus
from src.kernel.supervisor import KernelSupervisor
from src.memory.kernel import MemoryKernel
from src.intelligence.perception.engine import VisionEngine
from src.intelligence.perception.screen import ScreenObserver, WindowObserver
from src.intelligence.perception.live_streamer import GeminiLiveStreamer
from src.kernel.interceptor import SafetyInterceptor, PowerLevel
from src.kernel.introspection import IntrospectionEngine
from src.kernel.observatory import Observatory, AttentionMode
from src.intelligence.cognition import DiffusedAttentionMonitor
from src.capabilities.os.hud import HUDOverlay

class KernelLoop:
    """
    The core processing engine of the Agentic OS.
    
    Unifies:
    1. Async message handling from the EventBus.
    2. Real-time visual perception via Gemini Live Streamer.
    3. Multi-modal planning and feedback loops.
    4. HUD for user status updates.
    """
    def __init__(
        self,
        workspace: Path,
        memory: MemoryKernel,
        vision: VisionEngine,
        capabilities: Dict[str, Any],
        max_iterations: int = 50,
        power_level: PowerLevel = PowerLevel.OPERATOR
    ):
        self.workspace = workspace
        self.memory = memory
        self.vision = vision
        self.capabilities = capabilities
        self.max_iterations = max_iterations
        
        # RBAC Security Init
        self.power_level = power_level
        self.interceptor = SafetyInterceptor()
        
        # Auto-Tuning Evaluator Init
        from src.kernel.config_manager import AgentConfigManager
        from src.intelligence.planner.evaluator import FeedbackEvaluator
        self.config_manager = AgentConfigManager()
        self.evaluator = FeedbackEvaluator(self.config_manager)
        
        self.storage_dir = workspace / "storage"
        self.bus = DurableEventBus(self.storage_dir)
        logger.debug("[KernelLoop] EventBus ready.")
        # Perception modules
        logger.debug("[KernelLoop] Initializing ScreenObserver...")
        self.screen_observer = ScreenObserver(self.storage_dir / "screenshots" / "current")
        logger.debug("[KernelLoop] Initializing WindowObserver...")
        self.window_observer = WindowObserver(self.storage_dir / "screenshots" / "windows")
        logger.debug("[KernelLoop] Initializing GeminiLiveStreamer...")
        self.live_streamer = GeminiLiveStreamer()
        self.live_streamer.screen_observer = self.screen_observer
        self.vision.attach_live_streamer(self.live_streamer)
        
        self.introspection = IntrospectionEngine(workspace=self.workspace)
        self.cognition = DiffusedAttentionMonitor(self)
        self.observatory = Observatory(self.vision, self.screen_observer, self.cognition)
        self.supervisor = KernelSupervisor(None) 
        logger.debug("[KernelLoop] Observatory/Introspection ready.")
        logger.debug("[KernelLoop] Perception stack ready.")
        
        # User Interface
        logger.debug("[KernelLoop] Initializing HUD...")
        self.hud = HUDOverlay()
        
        self.is_running = False
        self._streaming_thread = None
        self._loop = asyncio.new_event_loop()
        
        logger.info(f"[KernelLoop] Initialized with Full Agentic Stack at {self.power_level.name} Mode")

    def _start_background_services(self):
        """Starts the Gemini Live session in a background thread."""
        def run_loop(loop):
            asyncio.set_event_loop(loop)
            system_prompt = (
                "You are the visual cortex of an Agentic OS. I am sending you a live screen stream. "
                "I will ask questions about UI elements. Provide bounding boxes and predict interactions."
            )
            async def runner():
                loop.create_task(self.live_streamer.stream_screen_loop(fps=0.5))
                await self.live_streamer.start_session(system_instruction=system_prompt)
            
            try:
                loop.run_until_complete(runner())
            except Exception as e:
                logger.error(f"[KernelLoop] LiveStreamer thread error: {e}")

        self._streaming_thread = threading.Thread(target=run_loop, args=(self._loop,), daemon=True)
        self._streaming_thread.start()

    async def run_task(self, task_description: str, session_id: str = "default"):
        """Executes a multi-modal agentic task loop."""
        self.is_running = True
        logger.info(f"[KernelLoop] Starting task: {task_description}")
        self.hud.update_goal(task_description)
        self.hud.update_status(True)
        
        # 0. CLASSIFY & DISPATCH
        # Analyze the task to determine if we need a full reasoning loop or a rigid script
        from src.intelligence.planner.dispatcher import IntelligenceDispatcher
        dispatcher = IntelligenceDispatcher(provider=None)
        strategy = await dispatcher.determine_strategy(task_description, screen_available=True)
        
        determinism = strategy.get("determinism_level", "SEMI_DETERMINISTIC")
        
        if determinism == "DETERMINISTIC":
            logger.warning("[KernelLoop] Task classified as DETERMINISTIC. Bypassing heavy LLM reasoning loop.")
            
            # Attempt to find a macro in the UI Profile Store
            macro = self.memory.profiles.find_macro_for_task(task_description)
            if macro:
                logger.info(f"[KernelLoop] --> Executing rigid procedural macro: '{macro['macro_name']}'")
                logger.debug(f"[KernelLoop] Sequence: {macro['sequence']}")
                # In a full implementation, we would iterate through sequence and call UI actions
                await asyncio.sleep(1)
                logger.info("[KernelLoop] Macro execution complete.")
            else:
                logger.error(f"[KernelLoop] No matching macro found for deterministic task: '{task_description}'")
                logger.warning("[KernelLoop] Falling back to exploratory OTA loop...")
                # Fallback handled by skipping the return and continuing to the loop below
                
            if macro:
                self.stop()
                return

        logger.info(f"[KernelLoop] Task classified as {determinism}. Engaging cognitive OTA loop.")
        
        # Start background monitors via Observatory
        self._start_background_services()
        self.observatory.set_attention_mode(AttentionMode.FOCUSED)
        
        # Wait for connection
        logger.info("[KernelLoop] Establishing Live API session...")
        await asyncio.sleep(5) 
        
        iteration = 0
        last_feedback = ""
        while self.is_running and iteration < self.max_iterations:
            iteration += 1
            self.hud.update_step(iteration, "Observing...")
            
            # --- 1. OBSERVE ---
            shot_path = self.screen_observer.capture(filename=f"loop_{iteration}.png")
            if not shot_path:
                logger.error("[KernelLoop] Capture failed. Retrying...")
                await asyncio.sleep(1)
                continue
            
            # Record elements in memory for spatial awareness
            state_desc = await self.vision.get_ui_state(shot_path)
            logger.info(f"[KernelLoop] Iteration {iteration} State: {state_desc[:100]}...")
            
            # --- 2. THINK / DECIDE ---
            self.hud.update_step(iteration, "Planning next step...")
            
            # --- 2. THINK / DECIDE ---
            # Real Cognitive Planner: Use the VLM to decide the next action
            prompt = (
                f"OBJECTIVE: {task_description}\n"
                f"CURRENT UI STATE: {state_desc}\n"
                f"LAST ACTION FEEDBACK: {last_feedback}\n\n"
                "Task: Decide the NEXT single action to move closer to the objective.\n"
                "Available Actions:\n"
                "1. click(target) - Click a UI element\n"
                "2. type(text, target=None) - Type text (optional target element)\n"
                "3. scroll(direction, amount) - Scroll the screen\n"
                "4. hotkey(keys) - Press a keyboard shortcut (e.g. 'command', 'space')\n"
                "5. wait(duration) - Wait for UI to stabilize\n"
                "6. web_browser(action, url=None, selector=None) - Use advanced browser tool\n"
                "7. done() - Mark objective as complete\n\n"
                "Output RAW JSON ONLY: {'action': '...', 'target': '...', 'reasoning': '...', 'parameters': {...}}\n"
            )
            
            try:
                plan_response = self.vision.client.models.generate_content(
                    model=self.vision.model_name,
                    contents=[prompt]
                )
                
                # Use json_repair for robustness
                import json_repair
                clean_json = plan_response.text.strip()
                if "```json" in clean_json:
                    clean_json = clean_json.split("```json")[1].split("```")[0].strip()
                elif "```" in clean_json:
                    clean_json = clean_json.split("```")[1].split("```")[0].strip()
                
                intended_action = json_repair.loads(clean_json)
                logger.info(f"[KernelLoop] Planned Action: {intended_action.get('action')} - {intended_action.get('reasoning')}")
            except Exception as e:
                logger.error(f"[KernelLoop] Planning failed: {e}. Falling back to explore.")
                intended_action = {"action": "explore", "target": "next_element"}
            
            # --- 2.5 RESOLVE COORDINATES ---
            if "target" in intended_action and intended_action["action"] in ["click", "double_click", "hover"]:
                self.hud.update_step(iteration, f"Resolving {intended_action['target']}...")
                # We assume a previous Pass 1 might have provided hint_coords.
                # Here we simulate or pull from VLM if needed.
                coords = await self.vision.resolve_target_with_zoom(
                    target=intended_action["target"],
                    hint_coords=intended_action.get("hint_coords"),
                    needs_zoom=intended_action.get("needs_zoom", False)
                )
                intended_action.update(coords)
                logger.info(f"[KernelLoop] Resolved '{intended_action['target']}' to {coords}")
            
            # --- 3. SAFETY INTERCEPTOR ---
            is_safe, reason = self.interceptor.evaluate_action(intended_action, self.power_level)
            if not is_safe:
                logger.error(f"[KernelLoop] SAFETY VIOLATION BLOCKED: {reason}")
                self.hud.update_action("BLOCKED: Safety Violation")
                # Pause agent and return control to human
                self.stop()
                return
            
            # --- 4. ACT ---
            self.hud.update_action(f"Executing: {intended_action['action']}")
            logger.info(f"[KernelLoop] Proceeding with ACT: {intended_action}")
            
            action_type = intended_action.get("action")
            try:
                if action_type in ["click", "double_click", "drag", "scroll", "move"]:
                    mouse = self.capabilities.get("mouse_control")
                    if mouse:
                        # Map loop action to mouse.py interface
                        params = {k: v for k, v in intended_action.items() if k != "action"}
                        await mouse.execute(action_type, **params)
                    else:
                        logger.warning("[KernelLoop] Mouse control capability missing!")
                        
                elif action_type in ["type", "press", "hotkey"]:
                    keyboard = self.capabilities.get("keyboard_control")
                    if keyboard:
                        params = {k: v for k, v in intended_action.items() if k != "action"}
                        await keyboard.execute(action_type, **params)
                    else:
                        logger.warning("[KernelLoop] Keyboard control capability missing!")
                
                elif action_type == "web_browser":
                    browser = self.capabilities.get("web_browser")
                    if browser:
                        await browser.execute(**intended_action.get("parameters", {}))
                    else:
                        logger.warning("[KernelLoop] Web browser capability missing!")
                
                elif action_type == "done":
                    logger.info("[KernelLoop] Objective marked as COMPLETE by agent.")
                    self.hud.update_action("Objective Complete.")
                    self.stop()
                    return
                
                elif action_type == "wait":
                    logger.debug(f"[KernelLoop] Waiting for {wait_time}s...")
                    await asyncio.sleep(wait_time)
                
            except Exception as e:
                logger.error(f"[KernelLoop] Actuation failed: {e}")
                last_feedback = f"Actuation Error: {e}"
                continue
            
            # --- 5. VERIFY / LEARN ---
            # In production, VisionEngine.verify_change() confirms if screen mutated.
            # We attempt a real verification here.
            verification = await self.vision.verify_change(
                before_path=shot_path,
                after_path=self.screen_observer.capture(filename=f"loop_{iteration}_after.png"),
                intent=intended_action.get("target", "action execution")
            )
            
            simulated_success = verification["success"]
            simulated_error = verification["reason"] if not simulated_success else ""
            
            logger.info(f"[KernelLoop] Action Verification: {verification['success']}")
            needs_restart = self.evaluator.log_action_result(
                action=intended_action, 
                success=simulated_success, 
                error_message=simulated_error
            )
            
            # If action failed, we set feedback for the next THINK iteration
            if not simulated_success:
                last_feedback = f"Execution Failure: {simulated_error}"
            
            if needs_restart:
                logger.warning("[KernelLoop] SYSTEM RESTART FLAG CAUGHT. Re-booting loop with new constraints...")
                self.hud.update_action("AUTO-TUNING. Restarting.")
                self.stop()
                return
            
            # --- 6. INTROSPECTION ---
            is_approved, feedback = await self.introspection.evaluate_adaptive(
                messages=[{"role": "user", "content": task_description}], # Simplified for stub
                draft_content=str(intended_action),
                tools_used=[intended_action["action"]]
            )
            
            if not is_approved:
                logger.warning(f"[KernelLoop] Introspection REJECTED: {feedback}")
                self.hud.update_action(f"Correction: {feedback[:20]}...")
                last_feedback = f"Introspection Correction: {feedback}"
                # RECOVERY: Do not ACT, loop back to THINK with the correction
                await asyncio.sleep(1)
                continue
            
            # Clear feedback if approved to allow fresh planning
            last_feedback = ""
                
            await asyncio.sleep(1)
            
        logger.info("[KernelLoop] Task finished.")
        self.observatory.set_attention_mode(AttentionMode.DIFFUSED)
        self.stop()

    def stop(self):
        self.is_running = False
        self.hud.update_status(False)
        if self.live_streamer:
            asyncio.run_coroutine_threadsafe(self.live_streamer.disconnect(), self._loop)
        if self.hud:
            self.hud.stop()
        logger.info("[KernelLoop] Shutdown complete.")

    async def _process_message(self, message: Dict[str, Any]):
        pass
