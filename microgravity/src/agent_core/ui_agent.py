import time
import sys
import os
from typing import Dict, Any, Optional
from pathlib import Path

# Add the 'src' directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui_controller.mouse import MouseController
from ui_controller.keyboard import KeyboardController
from ui_controller.window_manager import WindowManager
from perception.screen import ScreenObserver, WindowObserver
from perception.vision_analyzer import VisionAnalyzer
from planning.goal_manager import GoalManager
from planning.action_predictor import ActionPredictor
from planning.learning_loop import LearningLoop
from planning.agentic_planner import AgenticPlanner
from agent_core.ui_memory_agent import UIMemoryAgent
from ui_controller.live_streamer import GeminiLiveStreamer
from ui_controller.hud_overlay import HUDOverlay
from agent_core.tools.browser_tool import BrowserTool
import win32gui
import win32con
import asyncio
import threading


class UIAgent:
    """
    The main orchestrator that ties together all modules:
    Perception, Planning, Action, Awareness, and Learning into a continuous loop.
    """
    def __init__(self):
        # Force project-wide DPI awareness for consistent coordinate mapping
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1) # PROCESS_SYSTEM_DPI_AWARE
            print("[UIAgent] DPI Awareness forced to PROCESS_SYSTEM_DPI_AWARE")
        except Exception as e:
            print(f"[UIAgent] Warning: Could not set DPI awareness: {e}")

        print("[UIAgent] Initializing agent modules...", flush=True)
        self.mouse = MouseController(base_speed=1.0)
        print("[UIAgent] Mouse initialized", flush=True)
        self.keyboard = KeyboardController(wpm=60)
        print("[UIAgent] Keyboard initialized", flush=True)
        
        self.workspace_path = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        self.memory_agent = UIMemoryAgent(self.workspace_path)
        print("[UIAgent] UI Memory Agent initialized", flush=True)
        
        # Inject short-term paths into observers
        screenshot_dir = str(self.memory_agent.short_term_dir / "screenshots")
        self.screen_observer = ScreenObserver(output_dir=screenshot_dir)
        print("[UIAgent] Screen observer initialized", flush=True)
        self.window_observer = WindowObserver(output_dir=screenshot_dir)
        print("[UIAgent] Window observer initialized", flush=True)
        
        self.browser_tool = BrowserTool(headless=False)
        print("[UIAgent] BrowserTool wrapper initialized", flush=True)
        
        # ═══ Layer 3: CVPipeline (Foundation) ═══
        try:
            from perception.cv_pipeline import CVPipeline
            self.cv_pipeline = CVPipeline()
            print("[UIAgent] CVPipeline initialized", flush=True)
        except Exception as e:
            print(f"[UIAgent] CVPipeline init failed (fallback mode): {e}")
            self.cv_pipeline = None
        
        # VisionAnalyzer with CVPipeline hook
        self.vision = VisionAnalyzer(cv_pipeline=self.cv_pipeline)
        print("[UIAgent] Vision analyzer initialized (CV pipeline:", "attached" if self.cv_pipeline else "none", ")", flush=True)
        
        # ═══ Layer 3: Stability Classifier ═══
        try:
            from perception.static_dynamic_classifier import StaticDynamicClassifier
            self.stability_classifier = StaticDynamicClassifier(cv_pipeline=self.cv_pipeline)
            print("[UIAgent] StaticDynamicClassifier initialized", flush=True)
        except Exception as e:
            print(f"[UIAgent] StaticDynamicClassifier init failed: {e}")
            self.stability_classifier = None
        
        # ═══ Layer 1: ElementBoundaryLearner ═══
        try:
            from perception.element_boundary_learner import ElementBoundaryLearner
            self.boundary_learner = ElementBoundaryLearner(cv_pipeline=self.cv_pipeline, vision_analyzer=self.vision)
            print("[UIAgent] ElementBoundaryLearner initialized", flush=True)
        except Exception as e:
            print(f"[UIAgent] ElementBoundaryLearner init failed: {e}")
            self.boundary_learner = None
        
        # ═══ Layer 1: OSAwareness ═══
        try:
            from perception.os_awareness import OSAwareness
            self.os_awareness = OSAwareness()
            print("[UIAgent] OSAwareness initialized", flush=True)
        except Exception as e:
            print(f"[UIAgent] OSAwareness init failed: {e}")
            self.os_awareness = None
        
        # ═══ Layer 2: AppCharacterizer ═══
        try:
            from perception.app_characterizer import AppCharacterizer
            self.app_characterizer = AppCharacterizer(cv_pipeline=self.cv_pipeline, vision_analyzer=self.vision, memory_agent=self.memory_agent)
            print("[UIAgent] AppCharacterizer initialized", flush=True)
        except Exception as e:
            print(f"[UIAgent] AppCharacterizer init failed: {e}")
            self.app_characterizer = None
        
        # ═══ Layer 5: ExperientialMemory ═══
        try:
            from planning.experiential_memory import ExperientialMemory
            memory_dir = str(self.workspace_path / "agent_memory" / "experiential")
            self.experiential_memory = ExperientialMemory(storage_dir=memory_dir)
            print("[UIAgent] ExperientialMemory initialized", flush=True)
        except Exception as e:
            print(f"[UIAgent] ExperientialMemory init failed: {e}")
            self.experiential_memory = None
        
        # ═══ Layer 4: SituationalAwareness ═══
        try:
            from planning.situational_awareness import SituationalAwareness
            self.situational_awareness = SituationalAwareness(
                os_awareness=self.os_awareness,
                app_characterizer=self.app_characterizer,
                cv_pipeline=self.cv_pipeline,
                boundary_learner=self.boundary_learner,
                stability_classifier=self.stability_classifier,
                memory=self.memory_agent,
            )
            print("[UIAgent] SituationalAwareness initialized", flush=True)
        except Exception as e:
            print(f"[UIAgent] SituationalAwareness init failed: {e}")
            self.situational_awareness = None

        # ═══ Phase 12 & 13: Advanced Learning Layers ═══
        try:
            from perception.edge_correlator import EdgeCorrelator
            from planning.action_outcome_tracker import ActionOutcomeTracker
            from planning.presumption_engine import PresumptionEngine
            from planning.postponed_judgement import PostponedJudgement

            self.edge_correlator = EdgeCorrelator()
            
            outcome_dir = str(self.workspace_path / "agent_memory" / "outcomes")
            self.outcome_tracker = ActionOutcomeTracker(storage_dir=outcome_dir)
            
            presumption_dir = str(self.workspace_path / "agent_memory" / "presumptions")
            self.presumption_engine = PresumptionEngine(storage_dir=presumption_dir)
            
            self.postponed_judgement = PostponedJudgement()
            
            print("[UIAgent] Advanced Learning modules initialized", flush=True)
        except Exception as e:
            print(f"[UIAgent] Learning modules init failed: {e}")
            self.outcome_tracker = None
            self.presumption_engine = None
            self.postponed_judgement = None
            self.edge_correlator = None
        
        # ═══ DecisionManager ═══
        try:
            from planning.decision_manager import DecisionManager
            self.decision_manager = DecisionManager(
                experiential_memory=self.experiential_memory,
                boundary_learner=self.boundary_learner,
                cv_pipeline=self.cv_pipeline,
                stability_classifier=self.stability_classifier,
                live_streamer=None,  # Set after live_streamer init
                vision_analyzer=self.vision,
                ui_memory_agent=self.memory_agent,
                presumption_engine=self.presumption_engine,  # Phase 13
                cv_logger=self.cv_logger,                  # Phase 11
            )
            print("[UIAgent] DecisionManager initialized", flush=True)
        except Exception as e:
            print(f"[UIAgent] DecisionManager init failed: {e}")
            self.decision_manager = None
        
        # ═══ Core Planning/Action modules (with awareness hooks) ═══
        self.goal_manager = GoalManager()
        self.predictor = ActionPredictor(
            self.vision, memory_agent=self.memory_agent, 
            screen_observer=self.screen_observer,
            decision_manager=self.decision_manager,
            cv_pipeline=self.cv_pipeline,
        )
        self.learning_loop = LearningLoop(
            self.vision, self.predictor,
            experiential_memory=self.experiential_memory,
            cv_pipeline=self.cv_pipeline,
            outcome_tracker=self.outcome_tracker,      # Phase 13
            presumption_engine=self.presumption_engine, # Phase 13
            postponed_judgement=self.postponed_judgement,# Phase 13
        )
        self.window_manager = WindowManager()
        print("[UIAgent] Planning and Management modules initialized", flush=True)
        
        # Initialize Gemini Live Streamer (Disabled by default until started)
        self.live_streamer = GeminiLiveStreamer()
        self.live_streamer.screen_observer = self.screen_observer
        self._streaming_thread = None
        self._loop = asyncio.new_event_loop()
        
        # Wire live_streamer into DecisionManager
        if self.decision_manager:
            self.decision_manager.live = self.live_streamer
        
        self.is_running = False
        self.hud = HUDOverlay() # Initialize HUD
        
        # --- Bootstrap Static GUI Map into CV Memory ---
        self._bootstrap_static_memory()
        print("[UIAgent] Bootstrap complete", flush=True)

    def _start_live_stream(self):
         """Starts the asyncio event loop in a background thread to maintain the WebSocket."""
         def run_loop(loop):
             asyncio.set_event_loop(loop)
             
             system_prompt = "You are a UI Assistant examining a live screen. I will send you questions about UI elements. Provide their bounding boxes and predict the correct human interaction (e.g. 'hover', 'single_click')."
             
             async def runner():
                 # Create the stream task which will internally sleep until self.is_streaming becomes True
                 async def safe_stream():
                      while not self.live_streamer.is_streaming:
                           await asyncio.sleep(0.5)
                      await self.live_streamer.stream_screen_loop(fps=0.5)
                      
                 loop.create_task(safe_stream())
                 
                 # Block on the context manager session
                 await self.live_streamer.start_session(system_instruction=system_prompt)
                 
             try:
                 loop.run_until_complete(runner())
             except Exception as e:
                 print(f"[UIAgent - LiveStreamer] Could not establish live session: {e}")
                 
         self._streaming_thread = threading.Thread(target=run_loop, args=(self._loop,), daemon=True)
         self._streaming_thread.start()

    def _stop_live_stream(self):
         """Safely shuts down the background WebSocket."""
         if self.live_streamer and self.live_streamer.is_streaming:
             asyncio.run_coroutine_threadsafe(self.live_streamer.disconnect(), self._loop)
         if self._loop.is_running():
             self._loop.call_soon_threadsafe(self._loop.stop)


    def _bootstrap_static_memory(self):
        """Finds the most recent gui_map and raw screenshot in agent_memory (LT and ST) and loads them."""
        import glob
        import os
        
        # Search in both Long-Term and Short-Term for the freshest map
        search_paths = [
            (self.memory_agent.long_term_dir / "predicted_outputs", self.memory_agent.long_term_dir / "raw_screenshots"),
            (self.memory_agent.short_term_dir / "predicted_outputs", self.memory_agent.short_term_dir / "diagnostics")
        ]
        
        all_json_files = []
        path_map = {}
        
        for json_dir, img_dir in search_paths:
            found = glob.glob(os.path.join(str(json_dir), "gui_map_*.json"))
            all_json_files.extend(found)
            for f in found:
                path_map[f] = img_dir

        if not all_json_files:
            print("[UIAgent] No static gui_map JSON found to bootstrap.")
            return
            
        latest_json = max(all_json_files, key=os.path.getctime)
        img_dir = path_map[latest_json]
        
        # Extract timestamp: gui_map_1234567.json -> 1234567
        filename = os.path.basename(latest_json)
        timestamp = filename.replace("gui_map_", "").replace(".json", "")
        
        # Find matching raw screenshot (might be capture_ or raw_)
        possible_images = [
            os.path.join(str(img_dir), f"capture_{timestamp}.png"),
            os.path.join(str(img_dir), f"raw_capture_{timestamp}.png")
        ]
        
        raw_image = next((img for img in possible_images if os.path.exists(img)), None)
        
        if raw_image:
            print(f"[UIAgent] Bootstrapping from LATEST Map: {latest_json}")
            self.predictor.load_static_map(latest_json, raw_image)
        else:
            print(f"[UIAgent] Missing matching raw screenshot for {latest_json}. Looked in {img_dir}")

    def receive_task(self, task_description: str):
        """Entry point for Swarm to hand off a task."""
        self.goal_manager.set_goal(task_description)
        self.hud.update_goal(task_description)

    def run(self):
        """
        The main Observe-Think-Act loop (legacy static plan mode).
        """
        self.is_running = True
        print("[UIAgent] Starting execution loop (legacy mode)...")
        
        # Boot up the Live Streamer in the background
        self._start_live_stream()
        self.hud.update_status(True)
        
        while self.is_running and not self.goal_manager.goal_completed():
            action = self.goal_manager.get_next_action()
            if not action:
                 time.sleep(1)
                 continue
                 
            self._execute_action(action)
            
        print("[UIAgent] Goal completed or execution stopped.")
        self._stop_live_stream()
        self.is_running = False

    def run_agentic(self, task: str):
        """
        New AGENTIC execution loop.
        
        Instead of pre-planning all steps, this loop:
          1. OBSERVE: Capture current screen
          2. DECIDE: Ask Gemini what to do next (one step at a time)
          3. RESOLVE: Get precise coordinates (with zoom if needed)
          4. ACT: Execute the single action
          5. VERIFY: Check if the action succeeded
          6. FEEDBACK: Send step summary to Live API to steer context
          7. LOOP: If goal not complete, go to step 1
        """
        self.is_running = True
        print("[UIAgent] ===========================================")
        print(f"[UIAgent]   AGENTIC MODE: {task}")
        print("[UIAgent] ===========================================")
        
        # Initialize agentic planner
        planner = AgenticPlanner(
            situational_awareness=self.situational_awareness,
            experiential_memory=self.experiential_memory,
            decision_manager=self.decision_manager
        )
        planner.set_goal(task)
        self.hud.update_goal(task)
        
        # Boot Live Streamer
        self._start_live_stream()
        print("[UIAgent] Waiting 8 seconds for Live API connection...")
        time.sleep(8)
        
        if self.live_streamer.is_streaming:
            self.hud.update_status(True)
            print("[UIAgent] Live Stream ACTIVE")
        else:
            self.hud.update_status(False, fallback_active=True)
            print("[UIAgent] Live Stream offline. Using static VLM for planning.")
        
        # === NEW: IN-PLACE WINDOW DETECTION ===
        existing_hwnd = None
        app_keywords = ["chrome", "notepad", "edge", "explorer", "calculator", "word", "excel", "powerpoint"]
        target_app = None
        for kw in app_keywords:
            if kw in task.lower():
                existing_hwnd = self.window_manager.get_hwnd_by_title(kw)
                if existing_hwnd:
                    target_app = kw
                    break
        
        if existing_hwnd:
            print(f"[UIAgent] Found existing '{target_app}' window. Focusing for in-place execution.")
            self.window_manager.focus_window(existing_hwnd)
            # Add a conceptual "pre-step" to the planner so it knows we're already set up
            planner.step_history.append({
                "step_num": 0,
                "action_type": "attach",
                "target": target_app,
                "success": True,
                "reasoning": f"Detected existing {target_app} window. Skipping launch.",
                "verification_note": "Window focused and ready."
            })
        
        # Main agentic loop
        while self.is_running and not planner.is_complete():
            try:
                # === STEP 1: OBSERVE ===
                timestamp = int(time.time() * 1000)
                screenshot_filename = f"observe_{timestamp}.png"
                screenshot_dir = str(self.memory_agent.short_term_dir / "screenshots")
                screenshot_path = self.screen_observer.capture(
                    filename=os.path.join(screenshot_dir, screenshot_filename)
                )
                
                if not screenshot_path:
                    print("[UIAgent] Screenshot capture failed. Retrying...")
                    time.sleep(1)
                    continue
                
                # === UPDATE AWARENESS STACK ===
                if self.situational_awareness:
                    try:
                        import cv2
                        frame = cv2.imread(screenshot_path)
                        if frame is not None:
                            self.situational_awareness.build_world_model(frame)
                    except Exception as e:
                        print(f"[UIAgent] Failed to update World Model: {e}")
                
                # === NEW: STEP 1.5 SUPERVISE BROWSER TOOL ===
                if hasattr(self, 'browser_tool') and self.browser_tool.is_running:
                    self.hud.update_step(planner.current_step, "Supervising Browser Tool...")
                    print(f"[UIAgent Supervision] Browser Tool is running objective: '{self.browser_tool._current_objective}'.")
                    
                    if self.live_streamer.is_streaming:
                        # Ask the Live API to visually verify if the tool is making progress
                        supervision_prompt = (
                            f"The Browser Tool is currently automating: '{self.browser_tool._current_objective}'. "
                            "Look at the screen. Is it making progress, or does it look stuck/failed? "
                            "Respond with strictly JSON: {\"status\": \"progressing\" | \"stuck\" | \"failed\", \"reason\": \"what you observe\"}"
                        )
                        
                        try:
                            future = asyncio.run_coroutine_threadsafe(
                                self.live_streamer.send_prompt(supervision_prompt),
                                self._loop
                            )
                            # Wait briefly for feedback
                            future.result(timeout=10.0)
                            
                            # Parse result
                            def _supervision_callback(data: Dict[str, Any]):
                                if "text_response" in data:
                                    import json
                                    try:
                                        res = json.loads(data["text_response"])
                                        status = res.get("status", "progressing")
                                        reason = res.get("reason", "")
                                        print(f"[UIAgent Supervision] Live API says: {status.upper()} - {reason}")
                                        
                                        if status in ["stuck", "failed"]:
                                            print(f"[UIAgent Supervision] Deciding to ABORT Browser Tool due to visual failure.")
                                            self.browser_tool.abort()
                                            planner.step_history.append({
                                                "step_num": planner.current_step,
                                                "action_type": "delegate_to_browser_tool",
                                                "success": False,
                                                "verification_note": f"Aborted by Supervisor: {reason}"
                                            })
                                    except Exception: pass
                            
                            self.live_streamer.set_callback(_supervision_callback)
                            # Let the stream process the callback
                            time.sleep(2)
                        except Exception as e:
                            print(f"[UIAgent Supervision] Live API check failed: {e}")
                    
                    # If it's still running, skip standard Agentic Planning and wait
                    if self.browser_tool.is_running:
                        time.sleep(3.0)
                        continue
                        
                # If we get here, the BrowserTool either finished naturally, was aborted, or isn't running.
                
                # === STEP 2: DECIDE ===
                self.hud.update_step(planner.current_step + 1, "Thinking...")
                next_action = planner.decide_next_step(screenshot_path)
                
                if next_action is None:
                    # Goal complete or failed
                    break
                
                action_desc = f"{next_action.get('action', '?')} on {next_action.get('target', next_action.get('text', ''))}"
                self.hud.update_action(action_desc)
                self.hud.update_step(
                    planner.current_step,
                    next_action.get('reasoning', action_desc)
                )
                
                # === NEW: PROACTIVE INTENT FEEDBACK ===
                # Tell the Live API what we're about to do before we do it
                if self.live_streamer.is_streaming:
                    intent_msg = f"Intent: {action_desc}. Reasoning: {next_action.get('reasoning', '')}"
                    self.live_streamer.send_step_feedback(intent_msg, self._loop)
                
                # === STEP 3: RESOLVE COORDINATES ===
                if next_action.get('target') and next_action['action'] in ['click', 'double_click']:
                    coords = self.predictor.resolve_target_with_zoom(
                        target=next_action['target'],
                        hint_coords=next_action.get('hint_coords'),
                        needs_zoom=next_action.get('needs_zoom', False),
                        live_streamer=self.live_streamer if self.live_streamer.is_streaming else None,
                        event_loop=self._loop
                    )
                    next_action.update(coords)
                    next_action['resolved_coords'] = coords  # Store for memory prejudice prevention
                    next_action['is_global'] = True # Mark as already global
                    print(f"[UIAgent] Resolved coordinates: ({coords.get('x')}, {coords.get('y')})")
                
                # === STEP 4: EXECUTE ===
                print(f"[UIAgent] Executing: {next_action.get('action')} -- {next_action.get('reasoning', '')}")
                self._execute_action(next_action)
                
                # === STEP 5: VERIFY ===
                after_timestamp = int(time.time() * 1000)
                after_filename = f"verify_{after_timestamp}.png"
                after_path = self.screen_observer.capture(
                    filename=os.path.join(screenshot_dir, after_filename)
                )
                
                if after_path:
                    success = planner.verify_step(next_action, after_path)
                    
                    if not success:
                        self.hud.update_step(planner.current_step, "FAILED -- re-evaluating...")
                else:
                    planner._record_step(next_action, success=True, 
                                        verification_note="After-screenshot unavailable")
                
                # === STEP 6: LIVE API FEEDBACK ===
                if self.live_streamer.is_streaming:
                    step_summary = planner.get_step_summary()
                    self.live_streamer.send_step_feedback(step_summary, self._loop)
                
                # Small pause between steps
                time.sleep(0.5)
                
            except KeyboardInterrupt:
                print("\n[UIAgent] Interrupted by user.")
                break
            except Exception as e:
                print(f"[UIAgent] Error in agentic loop: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(1)
        
        # Finalize episode for Phase 13 learning
        if hasattr(self, 'learning_loop'):
            self.learning_loop.finalize_episode(
                task=planner.goal,
                app_name=planner.situational_awareness.get_current_context().get("app_name", "Desktop") if planner.situational_awareness else "Desktop",
                app_class=planner.situational_awareness.get_current_context().get("app_class", "") if planner.situational_awareness else "",
                overall_success=planner.is_complete() and not planner._is_failed
            )

        # Cleanup
        self._stop_live_stream()
        self.is_running = False
        
        return planner.get_status()


    def _execute_action(self, action: Dict[str, Any]):
        """Executes a single logical action, predicting parameters and evaluating success."""
        
        target = action.get('target', '')
        target_app = action.get('app_window')
        context = target_app if target_app else 'Desktop'
        timestamp = int(time.time()*1000)
        
        # Inject the live streamer into the action context for the predictor
        action['live_streamer'] = self.live_streamer
        self.hud.update_action(f"{action.get('action')} on {target}")
        
        # 1. Prediction with skip-perception hint
        # We try a 'dry run' of prediction to see if we can skip the screenshot
        params = None
        # Actions that don't require visual target prediction
        if action['action'] in ['wait', 'type', 'press', 'hotkey'] or not target:
            params = {"predicted_as": "no_target"}
        
        if params is None:
            if not self.live_streamer.is_streaming:
                 params = self.predictor.predict_action_parameters(action, screen_image_path=None)
        
        state_before = None

        if params is not None and params.get("predicted_as") == "invariant":
            print(f"[UIAgent] Optimization: Skipping 'before' screenshot for invariant '{target}' in stable context.")
        else:
            # Observe Before State: If action specifies an app window, capture just that
            if target_app:
                print(f"[UIAgent] Capturing background buffer for app '{target_app}'")
                filename = f"before_{target_app}_{timestamp}.png"
                full_path = str(self.memory_agent.short_term_dir / "screenshots" / filename)
                state_before = self.window_observer.capture_window_by_title(target_app, filename=full_path)
                # Fallback to full screen if window not found
                if not state_before:
                    filename = f"before_fallback_{timestamp}.png"
                    full_path = str(self.memory_agent.short_term_dir / "screenshots" / filename)
                    state_before = self.screen_observer.capture(filename=full_path)
            else:
                filename = f"before_{timestamp}.png"
                full_path = str(self.memory_agent.short_term_dir / "screenshots" / filename)
                state_before = self.screen_observer.capture(filename=full_path)
            
            # Re-predict with actual image (or trigger live async query natively if streaming)
            # SKIP if we already have no_target params
            if (not params or self.live_streamer.is_streaming) and (params is None or params.get("predicted_as") != "no_target"):
                
                # If streaming, we must block on the Async result from the predictor bridge
                if self.live_streamer.is_streaming:
                     # This is slightly tricky since _execute_action is sync, but we use threadsafe futures
                     import concurrent.futures
                     future = asyncio.run_coroutine_threadsafe(
                         self.predictor._query_live_api_with_zoom(target, action, self.live_streamer), 
                         self._loop
                     )
                     try:
                         # Wait for the WebSocket trip
                         params = future.result(timeout=20.0)
                     except Exception as e:
                         print(f"[UIAgent] Live prediction failed/timeout: {e}. Falling back to static.")
                         params = self.predictor.predict_action_parameters(action, state_before)
                else:
                     params = self.predictor.predict_action_parameters(action, state_before)

        
        # 2. Act (Coordinate Translation & Focus)
        import win32gui # win32con is not needed here anymore
        hwnd = None
        if target_app:
             hwnd = self.window_manager.get_hwnd_by_title(target_app)
             if hwnd:
                  self.window_manager.focus_window(hwnd)
                  # Coordinate translation logic: 
                  # ONLY translate if coords are relative (NOT marked as is_global)
                  if isinstance(params, dict) and 'x' in params and 'y' in params and not action.get('is_global'):
                      try:
                          client_point = win32gui.ClientToScreen(hwnd, (0, 0))
                          params['x'] = params['x'] + client_point[0]
                          params['y'] = params['y'] + client_point[1]
                          print(f"[UIAgent] Translated relative to global desktop ({params['x']}, {params['y']})")
                      except Exception: pass

        print(f"[UIAgent] Executing {action['action']} with {params}")
        
        # Action Dispatcher
        if action['action'] == 'click':
             if isinstance(params, dict) and 'x' in params and 'y' in params:
                 self.mouse.move_and_click(params['x'], params['y'], human_like=True)
             else:
                 print(f"[UIAgent] WARNING: Could not resolve coordinates for click on {action.get('target')}")
                 
        elif action['action'] == 'double_click':
             if isinstance(params, dict) and 'x' in params and 'y' in params:
                 self.mouse.move_to(params['x'], params['y'], human_like=True)
                 self.mouse.double_click()

        elif action['action'] == 'drag':
             # Resolve destination
             dest_label = action.get('destination')
             dest_params = self.predictor.predict_action_parameters({"action": "click", "target": dest_label}, state_before)
             if 'x' in params and 'y' in params and 'x' in dest_params:
                 self.mouse.drag_to(dest_params['x'], dest_params['y'], source_x=params['x'], source_y=params['y'])

        elif action['action'] == 'type':
             if 'text' in action:
                 self.keyboard.type_text(action['text'])
                 
        elif action['action'] == 'scroll':
             clicks = action.get('amount', 300)
             direction = action.get('direction', 'down')
             self.mouse.scroll(clicks, direction)

        elif action['action'] == 'minimize':
             if hwnd: self.window_manager.minimize(hwnd)
             
        elif action['action'] == 'maximize':
             if hwnd: self.window_manager.maximize(hwnd)

        elif action['action'] == 'resize':
             if hwnd and 'width' in action and 'height' in action:
                  self.window_manager.resize(hwnd, action['width'], action['height'])
                  
        elif action['action'] == 'hotkey':
             if 'keys' in action:
                 self.keyboard.hotkey(*action['keys'])
                 
        elif action['action'] == 'press':
             if 'key' in action:
                 self.keyboard.press_key(action['key'])
                 
        elif action['action'] == 'wait':
             time.sleep(action.get('duration', 1.0))
             
        elif action['action'] == 'focus_window':
             if 'hwnd' in action:
                  self.window_manager.focus_window(action['hwnd'])
             elif hwnd:
                  self.window_manager.focus_window(hwnd)
             
        elif action['action'] == 'delegate_to_browser_tool':
             objective = action.get('objective', action.get('text', 'unknown objective'))
             print(f"[UIAgent] Delegating to Browser Tool for objective: {objective}")
             if hasattr(self, 'browser_tool'):
                 self.browser_tool.execute_objective(objective)
             else:
                 print("[UIAgent] Cannot delegate: BrowserTool not initialized.")

        # ── CV Tool Dispatchers (function-calling from planner) ──
        elif action['action'] == 'cv_template_match':
             label = action.get('target_label', action.get('target', ''))
             threshold = action.get('threshold', 0.80)
             print(f"[UIAgent:CV] Template match requested for '{label}' (threshold={threshold})")
             current_screen = self.screen_observer.capture_as_numpy()
             atlas_template = self.memory_agent.recall_template(context or 'Desktop', label) if hasattr(self.memory_agent, 'recall_template') else None
             if current_screen is not None and atlas_template is not None:
                 result = self.cv_pipeline.match_template_multiscale(
                     current_screen, atlas_template, threshold=threshold,
                     target_label=label, mode="ACTIVE",
                 )
                 action['cv_result'] = result or {"matched": False}
             else:
                 action['cv_result'] = {"matched": False, "reason": "no template in atlas"}

        elif action['action'] == 'cv_snip_element':
             label = action.get('element_label', '')
             bbox = action.get('bbox', [])
             print(f"[UIAgent:CV] Snip & save element '{label}' at {bbox}")
             if bbox and len(bbox) == 4:
                 current_screen = self.screen_observer.capture_as_numpy()
                 if current_screen is not None:
                     x, y, w, h = bbox
                     crop = current_screen[y:y+h, x:x+w]
                     if crop.size > 0:
                         self.memory_agent.store_template(context or 'Desktop', label, crop)
                         self.cv_pipeline.logger.log_snip_save(label, bbox, "planner_request", False, "ACTIVE")
                         action['cv_result'] = {"saved": True}
                     else:
                         action['cv_result'] = {"saved": False, "reason": "empty crop"}

        elif action['action'] == 'cv_fingerprint_compare':
             label = action.get('element_label', '')
             print(f"[UIAgent:CV] Fingerprint compare for '{label}'")
             action['cv_result'] = {"same_state": True, "similarity": 0.0, "note": "no stored fingerprint"}

        elif action['action'] == 'cv_stability_check':
             region = action.get('region', [])
             print(f"[UIAgent:CV] Stability check for region {region}")
             stability = self.cv_pipeline.classify_regions(self.screen_observer.capture_as_numpy() or __import__('numpy').zeros((100,100,3), dtype=__import__('numpy').uint8))
             action['cv_result'] = {"classification": "STATIC", "stability_map_size": len(stability)}

        elif action['action'] == 'cv_embedding_search':
             desc = action.get('target_description', '')
             print(f"[UIAgent:CV] Embedding search for '{desc}'")
             action['cv_result'] = {"results": [], "note": "embedding search requires atlas data"}

        # ── Edge Correlation Tool Dispatchers ──
        elif action['action'] == 'cv_edge_detect':
             print("[UIAgent:CV] Running edge detection + CID assignment")
             current_screen = self.screen_observer.capture_as_numpy()
             if current_screen is not None and hasattr(self, 'edge_correlator'):
                 from perception.cv_pipeline import UIElement
                 elements = self.cv_pipeline.detect_ui_elements(current_screen)
                 elem_dicts = [{"x": e.x, "y": e.y, "width": e.width, "height": e.height,
                                "element_type": e.element_type, "label": e.label,
                                "confidence": e.confidence} for e in elements]
                 result = self.edge_correlator.full_correlate(current_screen, elem_dicts)
                 action['cv_result'] = {
                     "total_elements": result["total_elements"],
                     "edge_density_pct": result["edge_density_pct"],
                     "vlm_index": result["vlm_index"],
                     "structural_diff": result["structural_diff"],
                 }
             else:
                 action['cv_result'] = {"error": "edge_correlator not initialized"}

        elif action['action'] == 'cv_structural_map':
             print("[UIAgent:CV] Returning structural map")
             if hasattr(self, 'edge_correlator'):
                 summary = self.edge_correlator.get_registry_summary()
                 action['cv_result'] = summary
             else:
                 action['cv_result'] = {"error": "edge_correlator not initialized"}

        elif action['action'] == 'cv_find_by_cid':
             cid = action.get('cid', '')
             print(f"[UIAgent:CV] Looking up CID: {cid}")
             if hasattr(self, 'edge_correlator'):
                 ce = self.edge_correlator.find_element_by_cid(cid)
                 if ce:
                     action['cv_result'] = {
                         "found": True, "cid": cid,
                         "x": ce.x, "y": ce.y, "w": ce.width, "h": ce.height,
                         "center_x": ce.x + ce.width // 2,
                         "center_y": ce.y + ce.height // 2,
                         "label": ce.label, "type": ce.element_type,
                         "structural_context": ce.structural_context,
                     }
                 else:
                     action['cv_result'] = {"found": False, "cid": cid}
             else:
                 action['cv_result'] = {"error": "edge_correlator not initialized"}
             
        # Add a small human pause after action
        time.sleep(0.5)
        
        # 4. Observe After State
        if target_app:
            filename = f"after_{target_app}_{timestamp}.png"
            full_path = str(self.memory_agent.short_term_dir / "screenshots" / filename)
            state_after = self.window_observer.capture_window_by_title(target_app, filename=full_path)
            if not state_after:
                filename = f"after_fallback_{timestamp}.png"
                full_path = str(self.memory_agent.short_term_dir / "screenshots" / filename)
                state_after = self.screen_observer.capture(filename=full_path)
        else:
            filename = f"after_{timestamp}.png"
            full_path = str(self.memory_agent.short_term_dir / "screenshots" / filename)
            state_after = self.screen_observer.capture(filename=full_path)
        
        # 5. Evaluate Success (Learning)
        # Skip evaluation for transient or targetless actions
        success = True
        if action['action'] not in ['press', 'hotkey', 'wait'] and target:
            success = self.learning_loop.evaluate_action_success(action, state_before, state_after)
        
        if not success:
             print("[UIAgent] Action failed. Triggering Semantic Recovery Replan...")
             self.goal_manager.replan_recovery(action, state_after, self.vision)

if __name__ == "__main__":
    agent = UIAgent()
    agent.run_agentic_loop("Close the Notepad application.")
