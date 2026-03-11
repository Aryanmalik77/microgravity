import os
import asyncio
from PIL import Image
from typing import Dict, Any, List, Optional
from loguru import logger
from google import genai
from google.genai import types

class VisionEngine:
    """
    The visual cortex of the Agentic OS.
    Handles:
    1. Spatial Understanding (VLM)
    2. UI State Extraction
    3. Motion & State Diffing
    4. Fast Heuristic Detection (CV)
    """
    def __init__(self, memory_kernel: Any, model_name: str = "gemini-2.0-flash", api_key: str | None = None):
        from microgravity.config.loader import load_config
        self._config = load_config()
        self.api_key = api_key or self._config.providers.gemini.api_key
        
        if not self.api_key:
            logger.warning("[VisionEngine] Gemini API key not found in config.")
            
        self.model_name = model_name
        self.memory_kernel = memory_kernel
        # Initialize client with explicit API key
        self.client = genai.Client(api_key=self.api_key)
        self.live_streamer: Optional[Any] = None
        logger.info("[VisionEngine] Initialized with model {}", model_name)

    def attach_live_streamer(self, live_streamer: Any):
        self.live_streamer = live_streamer
        logger.info("[VisionEngine] Live Streamer attached.")

    async def find_element(self, image_path: str, description: str) -> Optional[Dict[str, Any]]:
        """Finds an element using the VLM's spatial tool and returns its center coordinates."""
        # If live streamer is active, we could theoretically query it here too
        logger.info(f"[VisionEngine] Finding '{description}' in {image_path}")
        try:
            img = Image.open(image_path)
            # Use specific spatial tool prompt format
            prompt = f"Detect the bounding box of the following element: '{description}'. Return in [ymin, xmin, ymax, xmax] normalized format."
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[img, prompt]
            )
            
            # Simple parsing for [ymin, xmin, ymax, xmax]
            text = response.text
            import re
            match = re.search(r"\[(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\]", text)
            if match:
                ymin, xmin, ymax, xmax = map(int, match.groups())
                # Return center normalized (0-1000)
                return {
                    "x": (xmin + xmax) // 2,
                    "y": (ymin + ymax) // 2,
                    "bbox": [ymin, xmin, ymax, xmax]
                }
            return None
        except Exception as e:
            logger.error(f"[VisionEngine] Error: {e}")
            return None

    async def get_ui_state(self, image_path: str) -> str:
        """Extracts structured UI state using VLM."""
        logger.info(f"[VisionEngine] Extracting state from {image_path}")
        try:
            img = Image.open(image_path)
            prompt = "Context: This is a screenshot of a web application or desktop. Task: Describe the current page state, major windows, and primary action buttons."
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[img, prompt]
            )
            return response.text
        except Exception as e:
            logger.error(f"[VisionEngine] Error: {e}")
            return "Error extracting UI state."

    async def verify_change(self, before_path: str, after_path: str, intent: str) -> Dict[str, Any]:
        """Semantically verifies if an action achieved its intent by comparing before/after states."""
        logger.info(f"[VisionEngine] Verifying intent: {intent}")
        try:
            img_before = Image.open(before_path)
            img_after = Image.open(after_path)
            prompt = f"Intent: {intent}. Task: Compare these two screenshots and determine if the intent was successfully achieved. Answer only 'YES' or 'NO' followed by a brief reason."
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[img_before, img_after, prompt]
            )
            success = "YES" in response.text.upper()
            return {"success": success, "reason": response.text}
        except Exception as e:
            logger.error(f"[VisionEngine] Error: {e}")
            return {"success": False, "reason": str(e)}

    async def resolve_target_with_zoom(self, target: str, hint_coords: Optional[List[int]] = None, 
                                     needs_zoom: bool = False) -> Dict[str, Any]:
        """
        Resolves a target to global pixel coordinates using a two-pass zoom strategy if needed.
        """
        logger.info(f"[VisionEngine] Resolving '{target}' (zoom={needs_zoom}, hint={hint_coords})")
        
        # 1. Check Memory (Spatial Atlas)
        # Using 'Desktop' as default context for now
        cached = self.memory_kernel.recall_element("Desktop", target)
        if cached and cached.get("is_invariant"):
             c = cached["coords"]
             # x, y, w, h
             return {"x": c[0] + c[2]//2, "y": c[1] + c[3]//2, "source": "memory"}

        # 2. If no Live Streamer, fallback to static find_element
        if not self.live_streamer or not self.live_streamer.is_streaming:
            logger.warning("[VisionEngine] Live Streamer not active. Fallback to static.")
            # We would need a recent screenshot path here. For now, using a stub.
            return {"x": 960, "y": 540} # Fallback to center

        # 3. Two-Pass Zoom Logic
        try:
            if needs_zoom or self._is_small_target(hint_coords):
                logger.info("[VisionEngine] Triggering PASS 2 (Closeup/Zoom)")
                result = await self._zoom_resolve(target, hint_coords)
                if result:
                    # Store in memory for future
                    self.memory_kernel.remember_element("Desktop", target, {
                        "coords": [result["x"] - 20, result["y"] - 20, 40, 40], # Estimating bbox
                        "type": "zoom_resolved",
                        "is_invariant": True
                    })
                    return result
            else:
                # Standard mapping
                screen_w, screen_h = self.live_streamer.screen_size
                if hint_coords:
                    gx = int((hint_coords[1] / 1000) * screen_w)
                    gy = int((hint_coords[0] / 1000) * screen_h)
                    return {"x": gx, "y": gy, "source": "hint"}
        except Exception as e:
            logger.error(f"[VisionEngine] Zoom resolution failed: {e}")

        return {"x": 960, "y": 540}

    def _is_small_target(self, hint_coords: Optional[List[int]]) -> bool:
        if not hint_coords: return True
        # If near edges or simply requested
        y, x = hint_coords
        if y > 900 or y < 100 or x > 900 or x < 100:
            return True
        return False

    async def _zoom_resolve(self, target: str, hint_coords: Optional[List[int]]) -> Optional[Dict[str, Any]]:
        from src.intelligence.perception.roi import ROIManager
        
        screen_w, screen_h = self.live_streamer.screen_size
        if hint_coords:
            center_x = int((hint_coords[1] / 1000) * screen_w)
            center_y = int((hint_coords[0] / 1000) * screen_h)
        else:
            # Fallback pass 1 to find general area
            # (In a real implementation, we'd query Pass 1 here)
            center_x, center_y = screen_w // 2, screen_h // 2

        self.live_streamer.set_roi(center_x, center_y, zoom_factor=3.0)
        
        # Wait for sync (Optimized)
        await asyncio.sleep(0.5) 
        await self.live_streamer.send_frame_now()
        
        response_event = asyncio.Event()
        prediction = {}

        def _callback(data):
            if "bounding_box" in data:
                logger.info(f"[VisionEngine] Received bounding_box: {data['bounding_box']}")
                prediction.update(data)
                response_event.set()
            elif "text_response" in data:
                # Attempt to parse JSON from text
                try:
                    import json
                    parsed = json.loads(data["text_response"])
                    if "bounding_box" in parsed:
                        prediction.update(parsed)
                        response_event.set()
                except: pass

        logger.info("[VisionEngine] Setting callback and sending prompt...")
        self.live_streamer.set_callback(_callback)
        
        prompt = f"MAGNIFIED CLOSEUP: Precise center of '{target}'? Also, list all other visible UI labels and their center coordinates. Respond JSON: {{'bounding_box': [ymin, xmin, ymax, xmax], 'secondary_elements': [{{'label': '...', 'center': [y, x]}}]}}"
        await self.live_streamer.send_prompt(prompt)
        
        try:
            await asyncio.wait_for(response_event.wait(), timeout=10.0)
            if "bounding_box" in prediction:
                bbox = prediction["bounding_box"]
                nx = (bbox[1] + bbox[3]) / 2000
                ny = (bbox[0] + bbox[2]) / 2000
                roi = self.live_streamer.current_roi
                size = self.live_streamer.screen_size
                
                if roi and size:
                    gx, gy = ROIManager.map_to_global(nx, ny, roi, size)
                    
                    # Store secondary elements found in the closeup
                    for elem in prediction.get("secondary_elements", []):
                        snx, sny = elem["center"][1] / 1000, elem["center"][0] / 1000
                        sgx, sgy = ROIManager.map_to_global(snx, sny, roi, size)
                        self.memory_kernel.remember_element("Desktop", elem["label"], {
                            "coords": [sgx - 10, sgy - 10, 20, 20],
                            "type": "closeup_discovery",
                            "is_invariant": False
                        })
                    
                    return {"x": gx, "y": gy, "source": "zoom"}
                else:
                    logger.error(f"[VisionEngine] Missing ROI ({roi}) or Size ({size}) for mapping.")
        except Exception as e:
            logger.error(f"[VisionEngine] Internal error in _zoom_resolve: {e}")
        finally:
            self.live_streamer.reset_roi()
            
        return None
