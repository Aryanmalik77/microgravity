from typing import Dict, Any, Optional
import json
import os
import cv2
import numpy as np
import asyncio
from perception.roi_manager import ROIManager

class ActionPredictor:
    """
    Predicts the required coordinates or keystrokes for a given logical action 
    based on the current screen state. Uses a Hybrid CV+VLM approach:
    1. Fast Path: DecisionManager multi-tier resolution (0ms - 50ms)
    2. Medium Path: OpenCV Template Matching (Zero Latency, < 10ms)
    3. Fallback Path: VLM Query (High Latency, 5-10s)
    """
    def __init__(self, vision_analyzer, memory_agent=None, screen_observer=None, 
                 decision_manager=None, cv_pipeline=None):
        self.vision = vision_analyzer
        self.memory_agent = memory_agent
        self.screen_observer = screen_observer
        self.decision_manager = decision_manager  # Multi-tier resolution pipeline
        self.cv_pipeline = cv_pipeline            # Advanced CV processing
        # RAM Cache: { "target_label": {"coords": (x,y), "template": numpy_bgr_array, "bbox": (x,y,w,h)} }
        self.memory = {}


    def load_static_map(self, json_path: str, raw_image_path: str):
        """Bootstraps the CV memory cache with thousands of templates from a static GUI map run."""
        if not os.path.exists(json_path) or not os.path.exists(raw_image_path):
            print(f"[ActionPredictor] Bootstrap files not found: {json_path} or {raw_image_path}")
            return
            
        print(f"[ActionPredictor] Bootstrapping Memory from {json_path}...")
        try:
            with open(json_path, 'r') as f:
                gui_map = json.load(f)
                
            raw_img = cv2.imread(raw_image_path)
            if raw_img is None:
                return
                
            loaded_count = 0
            for element in gui_map:
                label = element.get('label')
                # Ignore generic structural labels, keep semantic ones
                if label and label not in ["STRUCTURAL", "TASKBAR"]:
                    coords = element.get('coordinates', {})
                    if not coords:
                        continue
                    x, y, w, h = coords.get('x', 0), coords.get('y', 0), coords.get('width', 0), coords.get('height', 0)
                    
                    # Crop template from raw image
                    # Ensure within bounds
                    x, y = max(0, x), max(0, y)
                    h, w = max(1, h), max(1, w)
                    template = raw_img[y:y+h, x:x+w]
                    
                    if template.size > 0:
                        center_x = x + (w // 2)
                        center_y = y + (h // 2)
                        self.memory[label.lower()] = {
                            "coords": (center_x, center_y),
                            "template": template,
                            "bbox": (x, y, w, h)
                        }
                        loaded_count += 1
            print(f"[ActionPredictor] Bootstrap Complete: {loaded_count} templates cached in RAM.")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[ActionPredictor] Bootstrap Failed: {e}")

    def _verify_with_cv(self, template: np.ndarray, current_screen_path: str, threshold: float = 0.85) -> Optional[tuple]:
        """Uses OpenCV template matching to find the template in the current screen. Ultra fast."""
        try:
            current_screen = cv2.imread(current_screen_path)
            if current_screen is None or template is None:
                return None
                
            # Perform normalized cross-correlation
            result = cv2.matchTemplate(current_screen, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            if max_val >= threshold:
                # Match found! Calculate new center based on where it was found
                h, w = template.shape[:2]
                top_left = max_loc
                center_x = top_left[0] + w // 2
                center_y = top_left[1] + h // 2
                print(f"[CV Tracker] MATCH {max_val:.2f} >= {threshold}. Fast Coords: ({center_x}, {center_y})")
                return (center_x, center_y)
            else:
                print(f"[CV Tracker] STALE {max_val:.2f} < {threshold}. Element vanished or changed.")
                return None
        except Exception as e:
            print(f"[CV Tracker] CV Error: {e}")
            return None

    def predict_action_parameters(self, action: Dict[str, Any], screen_image_path: str) -> Dict[str, Any]:
        """
        Takes an abstract action and the current screen, and returns concrete parameters.
        """
        print(f"[ActionPredictor] Predicting parameters for {action['action']} on '{action.get('target', action.get('text'))}'")
        
        target = action.get('target')
        target_key = target.lower() if target else None
        
        if target_key:
            # 1. Check RAM Cache
            if target_key in self.memory:
                print(f"[ActionPredictor] Target '{target}' found in RAM Cache. Verifying with CV...")
                cached_data = self.memory[target_key]
                fast_coords = self._verify_with_cv(cached_data["template"], screen_image_path)
                if fast_coords:
                    # Update Atlas if position shifted significantly
                    if self.memory_agent:
                        context = action.get('app_window', 'Desktop')
                        new_coords = [fast_coords[0] - cached_data["bbox"][2]//2, 
                                     fast_coords[1] - cached_data["bbox"][3]//2,
                                     cached_data["bbox"][2], 
                                     cached_data["bbox"][3]]
                        self.memory_agent.sync_element(context, target, new_coords)
                    
                    return {"x": fast_coords[0], "y": fast_coords[1]}
                del self.memory[target_key]
            
            # 2. Check Persistent UI Atlas
            if self.memory_agent:
                context = action.get('app_window', 'Desktop')
                atlas_data = self.memory_agent.recall_element(context, target)
                if atlas_data:
                    if atlas_data.get("is_invariant"):
                        # Check if context is stable (rect hasn't changed)
                        # If FIXED (Desktop), skip CV if coords exist
                        context_type = self.memory_agent.atlas["contexts"].get(context, {}).get("type", "DYNAMIC")
                        
                        # Invariants in FIXED contexts are always safe to reuse if screen size matches
                        if context_type == "FIXED" and atlas_data.get("coords"):
                            c = atlas_data["coords"]
                            print(f"[ActionPredictor] DIRECT prediction for FIXED invariant '{target}': ({c[0]}, {c[1]})")
                            return {"x": c[0] + c[2]//2, "y": c[1] + c[3]//2, "predicted_as": "invariant"}

                    print(f"[ActionPredictor] Target '{target}' found in UI Atlas. Verifying with CV...")
                    if atlas_data.get("template_path") and screen_image_path:
                        try:
                            template_cv = cv2.imread(atlas_data["template_path"])
                            screen_cv = cv2.imread(screen_image_path)
                            if template_cv is not None and screen_cv is not None:
                                res = cv2.matchTemplate(screen_cv, template_cv, cv2.TM_CCOEFF_NORMED)
                                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
                                if max_val >= 0.85:
                                    x, y = max_loc
                                    h, w = template_cv.shape[:2]
                                    print(f"[CV Tracker] Atlas MATCH {max_val:.2f} >= 0.85. Coords: ({x}, {y})")
                                    return {"x": x + w//2, "y": y + h//2}
                        except Exception as e:
                            print(f"[ActionPredictor] CV verification failed for Atlas template: {e}")
                            
                    # Fallback to coordinate-based prediction if template fails but we have bounds
                    if atlas_data.get("coords"):
                        # This is riskier as windows might move, but useful for static layouts
                        c = atlas_data["coords"]
                        
                        # Return interaction preference if known
                        pref = atlas_data.get("interaction_preference", "default")
                        return {"x": c[0] + c[2]//2, "y": c[1] + c[3]//2, "interaction_preference": pref}

        if action['action'] in ['click', 'request_closeup_zoom']:
            # --- 2. FALLBACK PATH: VLM Query ---
            print(f"[ActionPredictor] Target '{target}' not cached or stale. Falling back to VLM...")
            
            # --- NEW: Autonomous Zoom Heuristic & Explicit Request ---
            needs_zoom = action.get("needs_zoom", False) or action['action'] == 'request_closeup_zoom'
            
            # Use Live Stream if available, otherwise static vision
            live_streamer = action.get('live_streamer')
            
            if live_streamer and live_streamer.is_streaming:
                 # If explicit zoom requested OR we suspect it's tiny based on previous hints
                 if needs_zoom:
                     print(f"[ActionPredictor] ZOOM TRIGGERED for target: '{target}'")
                     # We must run this as a threadsafe future because predict_action_parameters is sync
                     try:
                         future = asyncio.run_coroutine_threadsafe(
                             self._query_live_api_with_zoom(target, action, live_streamer), 
                             live_streamer.loop
                         )
                         return future.result(timeout=15.0)
                     except Exception as e:
                         print(f"[ActionPredictor] Live API Zoom failed: {e}")
                 else:
                     # Standard Live API overview query
                     try:
                         future = asyncio.run_coroutine_threadsafe(
                             self._query_live_api_with_zoom(target, action, live_streamer), 
                             live_streamer.loop
                         )
                         return future.result(timeout=15.0)
                     except Exception as e:
                         print(f"[ActionPredictor] Live API Query failed: {e}")
                 
                 # If Live API fails, fallback to static
                 if screen_image_path is None:
                     return None
                 return self._query_static_vlm(target, action, screen_image_path, target_key)
            else:
                 if screen_image_path is None:
                     return None
                 return self._query_static_vlm(target, action, screen_image_path, target_key)

    async def _query_live_api_with_zoom(self, target: str, action: Dict[str, Any], live_streamer: Any) -> Dict[str, Any]:
        """Forces a two-pass zoom strategy on the Live Streamer context to find tiny elements."""
        print(f"[ActionPredictor] FORCED ZOOM PASS 1: Finding general area for '{target}'...")
        
        original_callback = live_streamer.on_response_callback
        response_event = asyncio.Event()
        prediction_result = {}
        
        def _live_callback(data: Dict[str, Any]):
            if "bounding_box" in data or "coordinates" in data or "verified" in data:
                 prediction_result.update(data)
                 response_event.set()
            elif "text_response" in data:
                 import json as _json
                 try:
                     parsed = _json.loads(data["text_response"])
                     prediction_result.update(parsed)
                 except Exception:
                     prediction_result["raw_text"] = data["text_response"]
                 response_event.set()
        
        live_streamer.set_callback(_live_callback)
        
        # Determine target text to send. If the action provided hint coords, we can skip pass 1!
        hint_coords = action.get("hint_coords")
        
        if hint_coords and len(hint_coords) == 2:
            print(f"[ActionPredictor] Hint coords provided: {hint_coords}. Skipping Overview Pass.")
            # hint_coords are [y_norm, x_norm] in % space (0-1000 typically)
            screen_w, screen_h = live_streamer.screen_size
            center_x = int((hint_coords[1] / 1000.0) * screen_w)
            center_y = int((hint_coords[0] / 1000.0) * screen_h)
            
            # Simulate a resolved pass 1
            bbox = [max(0, hint_coords[0]-10), max(0, hint_coords[1]-10), 
                    min(1000, hint_coords[0]+10), min(1000, hint_coords[1]+10)]
            prediction_result["bounding_box"] = bbox
            response_event.set()
        else:
            # PASS 1: OVERVIEW
            prompt_v1 = f"""
            Locate the UI element: '{target}'.
            Respond with [ymin, xmin, ymax, xmax] in normalized (0-1000) coordinates.
            JSON format: {{"bounding_box": [ymin, xmin, ymax, xmax]}}
            """
            await live_streamer.send_prompt(prompt_v1)
        
        try:
             await asyncio.wait_for(response_event.wait(), timeout=8.0)
             
             if "bounding_box" in prediction_result:
                 bbox = prediction_result["bounding_box"]
                 
                 # 1. Calculate global center for zoom from Pass 1
                 screen_w, screen_h = live_streamer.screen_size
                 center_x = int(((bbox[1] + bbox[3]) / 2000) * screen_w)
                 center_y = int(((bbox[0] + bbox[2]) / 2000) * screen_h)
                 
                 print(f"[ActionPredictor] PASS 2: Zooming into ({center_x}, {center_y}) for '{target}'...")
                 
                 # 2. Trigger Zoom
                 live_streamer.set_roi(center_x, center_y, zoom_factor=3.0)
                 
                 # 3. Wait for frame sync (approx 2 frames)
                 await asyncio.sleep(1.5)
                 
                 # 4. Re-query in closeup
                 response_event.clear()
                 prediction_result.clear()
                 
                 prompt_v2 = f"""
                 This is a MAGNIFIED CLOSEUP view centered around '{target}'.
                 Carefully locate the exact center of '{target}'.
                 Respond with [ymin, xmin, ymax, xmax] in local normalized (0-1000) coordinates.
                 JSON format: {{"bounding_box": [ymin, xmin, ymax, xmax]}}
                 """
                 await live_streamer.send_prompt(prompt_v2)
                 await asyncio.wait_for(response_event.wait(), timeout=8.0)
                 
                 if "bounding_box" in prediction_result:
                     bbox_roi = prediction_result["bounding_box"]
                     
                     # Map ROI normalized to Global Pixels
                     nx_center = (bbox_roi[1] + bbox_roi[3]) / 2000
                     ny_center = (bbox_roi[0] + bbox_roi[2]) / 2000
                     
                     gx, gy = ROIManager.map_to_global(nx_center, ny_center, live_streamer.current_roi, live_streamer.screen_size)
                     print(f"[ActionPredictor] ZOOM SUCCESS: Mapped ROI ({nx_center:.2f}, {ny_center:.2f}) -> Global ({gx}, {gy})")
                     
                     # ── NEW: Pass 3 - Pointer Verification ──
                     print(f"[ActionPredictor] PASS 3: Pointer Verification. Moving mouse to ({gx}, {gy})...")
                     try:
                         import pyautogui
                         # Move the physical mouse to the proposed coordinate
                         pyautogui.moveTo(gx, gy, duration=0.3)
                         # Wait for the video stream to capture the new mouse position
                         await asyncio.sleep(1.0)
                         
                         response_event.clear()
                         prediction_result.clear()
                         
                         prompt_v3 = f"""
                         Look at the tip of the mouse cursor in this zoomed-in view. 
                         Is the cursor pointing directly at the center of '{target}'?
                         Respond strictly in JSON: {{"verified": true}} or {{"verified": false}}
                         """
                         await live_streamer.send_prompt(prompt_v3)
                         await asyncio.wait_for(response_event.wait(), timeout=8.0)
                         
                         if prediction_result.get("verified") is True:
                             print("[ActionPredictor] POINTER VERIFIED! Target acquired.")
                             return {"x": gx, "y": gy, "interaction_preference": "single_click"}
                         else:
                             print("[ActionPredictor] POINTER VERIFICATION FAILED. Retrying with offset nudge...")
                             # Retry once with a small pixel offset
                             pyautogui.moveTo(gx + 3, gy + 3, duration=0.2)
                             await asyncio.sleep(0.5)
                             response_event.clear()
                             prediction_result.clear()
                             await live_streamer.send_prompt(prompt_v3)
                             await asyncio.wait_for(response_event.wait(), timeout=5.0)
                             if prediction_result.get("verified") is True:
                                 print("[ActionPredictor] POINTER VERIFIED on retry with nudge!")
                                 return {"x": gx + 3, "y": gy + 3, "interaction_preference": "single_click"}
                             raise Exception("Pointer Verification rejected the predicted coordinate after retry.")
                             
                     except Exception as verify_err:
                         print(f"[ActionPredictor] Pointer Verification Error/Failure: {verify_err}")
                         raise Exception(f"Pointer Verification failed: {verify_err}")
                         
                 else:
                     raise Exception("Pass 2 failed to output valid bounding box in closeup.")
             else:
                 raise Exception("Pass 1 failed to locate element overview.")
                 
        except Exception as e:
             print(f"[ActionPredictor] Live API Forced Zoom failed: {e}")
             # Let it fall through to static fallback or exception handler
             raise e
        finally:
             live_streamer.set_callback(original_callback)
             live_streamer.reset_roi()
        """Queries the active Gemini Live Streaming session with a two-pass Zoom strategy."""
        print(f"[ActionPredictor] PASS 1: Overview Query for '{target}'...")
        
        original_callback = live_streamer.on_response_callback
        response_event = asyncio.Event()
        prediction_result = {}
        
        def _live_callback(data: Dict[str, Any]):
            if "bounding_box" in data or "coordinates" in data:
                 prediction_result.update(data)
                 response_event.set()
            elif "text_response" in data:
                 prediction_result["raw_text"] = data["text_response"]
                 response_event.set()
        
        live_streamer.set_callback(_live_callback)
        
        # PASS 1: OVERVIEW
        prompt_v1 = f"""
        Locate the UI element: '{target}'.
        Respond with [ymin, xmin, ymax, xmax] in normalized (0-1000) coordinates.
        JSON format: {{"bounding_box": [ymin, xmin, ymax, xmax]}}
        """
        await live_streamer.send_prompt(prompt_v1)
        
        try:
             await asyncio.wait_for(response_event.wait(), timeout=8.0)
             
             if "bounding_box" in prediction_result:
                 bbox = prediction_result["bounding_box"]
                 
                 # Check if we need a Closeup (Pass 2)
                 # Heuristic: If width or height is < 5% of screen (50 units in 1000 range)
                 width = bbox[3] - bbox[1]
                 height = bbox[2] - bbox[0]
                 
                 if (width < 60 or height < 60) and live_streamer.current_roi is None:
                     print(f"[ActionPredictor] PASS 2: Closeup Needed. Target size: {width}x{height}")
                     
                     # 1. Calculate global center for zoom
                     screen_w, screen_h = live_streamer.screen_size
                     center_x = int(((bbox[1] + bbox[3]) / 2000) * screen_w)
                     center_y = int(((bbox[0] + bbox[2]) / 2000) * screen_h)
                     
                     # 2. Trigger Zoom
                     live_streamer.set_roi(center_x, center_y, zoom_factor=2.5)
                     
                     # 3. Wait for frame sync (approx 2 frames)
                     await asyncio.sleep(1.5)
                     
                     # 4. Re-query in closeup
                     response_event.clear()
                     prediction_result.clear()
                     
                     prompt_v2 = f"""
                     This is a MAGNIFIED CLOSEUP of the area around '{target}'.
                     Locate '{target}' precisely in this magnified view.
                     Respond in JSON: {{"bounding_box": [ymin, xmin, ymax, xmax], "interaction_preference": "single_click"}}
                     """
                     await live_streamer.send_prompt(prompt_v2)
                     await asyncio.wait_for(response_event.wait(), timeout=8.0)
                     
                     if "bounding_box" in prediction_result:
                         bbox_roi = prediction_result["bounding_box"]
                         pref = prediction_result.get("interaction_preference", "single_click")
                         
                         # Map ROI normalized to Global Pixels
                         nx_center = (bbox_roi[1] + bbox_roi[3]) / 2000
                         ny_center = (bbox_roi[0] + bbox_roi[2]) / 2000
                         
                         gx, gy = ROIManager.map_to_global(nx_center, ny_center, live_streamer.current_roi, live_streamer.screen_size)
                         
                         print(f"[ActionPredictor] Pass 2 Success: Mapped ({nx_center:.2f}, {ny_center:.2f}) -> Global ({gx}, {gy})")
                         
                         # Cleanup
                         live_streamer.reset_roi()
                         return {"x": gx, "y": gy, "interaction_preference": pref}

                 # Fallback to Pass 1 result if pass 2 wasn't needed or failed
                 screen_w, screen_h = live_streamer.screen_size
                 gx = int(((bbox[1] + bbox[3]) / 2000) * screen_w)
                 gy = int(((bbox[0] + bbox[2]) / 2000) * screen_h)
                 return {"x": gx, "y": gy, "interaction_preference": prediction_result.get("interaction_preference", "single_click")}
                 
        except asyncio.TimeoutError:
             print("[ActionPredictor] Live API query timed out. Falling back to static VLM.")
        except Exception as e:
             print(f"[ActionPredictor] Live API query failed: {e}. Falling back to static VLM.")
        finally:
             live_streamer.set_callback(original_callback)
             live_streamer.reset_roi()
             
        # Fallback to static VLM if live API fails to find the element
        screen_path = os.path.join(self.memory_agent.short_term_dir / "diagnostics", "live_fallback_capture.png")
        if not os.path.exists(screen_path):
             # Ensure we have an image to fallback on
             live_streamer._capture_screen_compressed() # Force a frame save to debug_dir if set
             import glob
             fallback_imgs = glob.glob(os.path.join(live_streamer.debug_dir, "*.jpg"))
             if fallback_imgs:
                 screen_path = max(fallback_imgs, key=os.path.getctime)
             else:
                 return {"x": 100, "y": 100} # Ultimate catastrophic fallback
        
        target_key = target.lower() if target else None
        return self._query_static_vlm(target, action, screen_path, target_key)

    def _query_static_vlm(self, target: str, action: Dict[str, Any], screen_image_path: str, target_key: str) -> Dict[str, Any]:
        """Original static image prompting logic."""
        vlm_response = self.vision.find_element_bbox(screen_image_path, target)
        
        try:
            if "NOT FOUND" not in vlm_response:
                # Clean the string and convert to a list of integers
                clean_text = vlm_response.replace('[', '').replace(']', '').strip()
                ymin, xmin, ymax, xmax = map(int, clean_text.split(','))
                
                # Get actual image dimensions & crop the new template
                img_cv = cv2.imread(screen_image_path)
                img_height, img_width = img_cv.shape[:2]
                
                # Convert Normalized 0-1000 bounds to Actual Screen Pixels
                pixel_xmin = int((xmin / 1000) * img_width)
                pixel_xmax = int((xmax / 1000) * img_width)
                pixel_ymin = int((ymin / 1000) * img_height)
                pixel_ymax = int((ymax / 1000) * img_height)
                
                center_x = (pixel_xmin + pixel_xmax) // 2
                center_y = (pixel_ymin + pixel_ymax) // 2
                
                print(f"[ActionPredictor] VLM Found '{target}' at: L:{pixel_xmin}, T:{pixel_ymin}, R:{pixel_xmax}, B:{pixel_ymax}")
                
                # Crop template and save to memory for NEXT time
                w = pixel_xmax - pixel_xmin
                h = pixel_ymax - pixel_ymin
                if w > 0 and h > 0:
                    new_template = img_cv[pixel_ymin:pixel_ymax, pixel_xmin:pixel_xmax]
                    self.memory[target_key] = {
                        "coords": (center_x, center_y),
                        "template": new_template,
                        "bbox": (pixel_xmin, pixel_ymin, w, h)
                    }
                    # Persist to Atlas for next session
                    if self.memory_agent:
                        context = action.get('app_window', 'Desktop')
                        self.memory_agent.remember_element(context, target, {
                            "coords": [pixel_xmin, pixel_ymin, w, h],
                            "type": "vlm_discovered"
                        }, template=new_template)
                    
                return {"x": center_x, "y": center_y}
        except Exception as e:
            print(f"[ActionPredictor ERROR] Failed to parse VLM output: {vlm_response}. Error: {e}")
            
        # Default fallback
        return {"x": 100, "y": 100}

    def resolve_target_with_zoom(self, target: str, hint_coords: list = None, 
                                  needs_zoom: bool = False, live_streamer=None,
                                  event_loop=None) -> Dict[str, Any]:
        """
        Standalone target resolution for the AgenticPlanner.
        
        Takes a target description and optional hint coordinates from the planner's
        Gemini decision, then resolves to precise pixel coordinates using:
          1. CV cache lookup (fast path)
          2. Live API two-pass zoom (if streaming and element is small)
          3. Static VLM fallback
        
        Args:
            target: Description of the UI element to find
            hint_coords: [y_norm, x_norm] in 0-1000 range from planner's Gemini response
            needs_zoom: Whether the planner flagged this as needing closeup
            live_streamer: GeminiLiveStreamer instance (optional)
            event_loop: asyncio event loop for the live streamer thread
            
        Returns:
            Dict with 'x' and 'y' pixel coordinates
        """
        print(f"[ActionPredictor] resolve_target_with_zoom('{target}', hint={hint_coords}, zoom={needs_zoom})")
        
        target_key = target.lower() if target else None
        
        # 1. Try CV cache first (fastest)
        if target_key and target_key in self.memory:
            # Capture a fresh screenshot for CV verification
            if self.screen_observer:
                screen_path = self.screen_observer.capture()
                if screen_path:
                    cached_data = self.memory[target_key]
                    fast_coords = self._verify_with_cv(cached_data["template"], screen_path)
                    if fast_coords:
                        print(f"[ActionPredictor] CV cache hit for '{target}': ({fast_coords[0]}, {fast_coords[1]})")
                        return {"x": fast_coords[0], "y": fast_coords[1]}
                    else:
                        del self.memory[target_key]
        
        # 2. If hint_coords provided and zoom needed, do two-pass zoom via Live API
        if hint_coords and live_streamer and live_streamer.is_streaming and event_loop:
            try:
                if needs_zoom or self._is_small_target(hint_coords, live_streamer.screen_size):
                    print(f"[ActionPredictor] Zoom resolution needed for '{target}'")
                    result = self._zoom_resolve_sync(target, hint_coords, live_streamer, event_loop)
                    if result:
                        return result
                else:
                    # Convert hint_coords directly to pixels (no zoom needed)
                    screen_w, screen_h = live_streamer.screen_size
                    gx = int((hint_coords[1] / 1000) * screen_w)
                    gy = int((hint_coords[0] / 1000) * screen_h)
                    print(f"[ActionPredictor] Direct coord mapping: ({gx}, {gy})")
                    return {"x": gx, "y": gy}
            except Exception as e:
                print(f"[ActionPredictor] Zoom resolution failed: {e}")
        
        # 3. If hint_coords available but no live streamer, use them directly
        if hint_coords:
            screen_w, screen_h = 1920, 1080 # default
            if live_streamer:
                screen_w, screen_h = live_streamer.screen_size
            elif self.screen_observer and hasattr(self.screen_observer, 'sct'):
                monitor = self.screen_observer.sct.monitors[1]
                screen_w, screen_h = monitor["width"], monitor["height"]
            
            gx = int((hint_coords[1] / 1000) * screen_w)
            gy = int((hint_coords[0] / 1000) * screen_h)
            return {"x": gx, "y": gy}
        
        # 4. Full VLM fallback: take screenshot and ask the static VLM
        if self.screen_observer:
            screen_path = self.screen_observer.capture()
            if screen_path:
                action = {"action": "click", "target": target}
                return self._query_static_vlm(target, action, screen_path, target_key)
        
        print(f"[ActionPredictor] WARNING: Could not resolve '{target}'. Using center screen fallback.")
        return {"x": 960, "y": 540}

    def _is_small_target(self, hint_coords: list, screen_size: tuple) -> bool:
        """Heuristic: check if a target at the given coordinates is likely small enough to need zoom."""
        # If hint_coords are near edges of screen, more likely to be small UI elements
        y, x = hint_coords
        if y > 920 or y < 80 or x > 920 or x < 80:
            return True
        return False

    def _zoom_resolve_sync(self, target: str, hint_coords: list, 
                           live_streamer, event_loop) -> Optional[Dict[str, Any]]:
        """
        Synchronous wrapper for the two-pass zoom resolution using Live API.
        
        Pass 1: Set ROI centered on hint_coords
        Pass 2: Query zoomed view for precise location
        """
        import concurrent.futures
        
        screen_w, screen_h = live_streamer.screen_size
        center_x = int((hint_coords[1] / 1000) * screen_w)
        center_y = int((hint_coords[0] / 1000) * screen_h)
        
        async def _async_zoom():
            # Set ROI for zoom
            live_streamer.set_roi(center_x, center_y, zoom_factor=2.5)
            
            # Wait for a few frames to sync
            await asyncio.sleep(1.5)
            
            # Send zoomed frame  
            await live_streamer.send_frame_now()
            await asyncio.sleep(0.5)
            
            # Query for precise location in zoomed view
            response_event = asyncio.Event()
            result_holder = {}
            original_callback = live_streamer.on_response_callback
            
            def _callback(data: Dict[str, Any]):
                result_holder.update(data)
                response_event.set()
            
            live_streamer.set_callback(_callback)
            
            prompt = f"""This is a MAGNIFIED CLOSEUP of the area around '{target}'.
Locate '{target}' precisely in this magnified view.
Respond in JSON: {{"bounding_box": [ymin, xmin, ymax, xmax], "found": true}}
Coordinates are normalized 0-1000."""
            
            await live_streamer.send_prompt(prompt)
            
            try:
                await asyncio.wait_for(response_event.wait(), timeout=8.0)
                
                if "bounding_box" in result_holder:
                    bbox = result_holder["bounding_box"]
                    nx_center = (bbox[1] + bbox[3]) / 2000
                    ny_center = (bbox[0] + bbox[2]) / 2000
                    
                    gx, gy = ROIManager.map_to_global(
                        nx_center, ny_center, 
                        live_streamer.current_roi, 
                        live_streamer.screen_size
                    )
                    print(f"[ActionPredictor] Zoom resolved: ({gx}, {gy})")
                    return {"x": gx, "y": gy}
            except asyncio.TimeoutError:
                print("[ActionPredictor] Zoom query timed out")
            finally:
                live_streamer.set_callback(original_callback)
                live_streamer.reset_roi()
            
            return None
        
        try:
            future = asyncio.run_coroutine_threadsafe(_async_zoom(), event_loop)
            return future.result(timeout=15.0)
        except Exception as e:
            print(f"[ActionPredictor] _zoom_resolve_sync failed: {e}")
            live_streamer.reset_roi()
            return None

    def record_outcome(self, action: Dict[str, Any], success: bool):
        """
        Updates memory if an action failed.
        """
        if not success:
             target = action.get('target')
             if target and target in self.memory:
                 print(f"[ActionPredictor] Action failed on '{target}'. Removing from memory.")
                 del self.memory[target]

