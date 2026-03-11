import json
import logging
import asyncio
import time
from typing import Any, Optional, Dict, List
from loguru import logger
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from src.common.tool import Tool
from src.memory.kernel import MemoryKernel

class HybridBrowserTool(Tool):
    """
    A unified web intelligence tool.
    Combines:
    1. Stealthy Selenium (Nanobot)
    2. Visual Verification (UI Agent)
    3. Memory-linked state tracking
    """
    @property
    def name(self) -> str:
        return "hybrid_browser"

    @property
    def description(self) -> str:
        return "Advanced web automation with stealth, DOM interaction, and visual verification."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["navigate", "click", "type", "screenshot", "get_state"]},
                "url": {"type": "string"},
                "selector": {"type": "string"},
                "text": {"type": "string"},
                "x": {"type": "integer"},
                "y": {"type": "integer"}
            },
            "required": ["action"]
        }

    def __init__(self, memory: MemoryKernel, headless: bool = False):
        self.memory = memory
        self.headless = headless
        self.driver: Optional[uc.Chrome] = None

    def _ensure_browser(self):
        if self.driver is None:
            logger.info("[HybridBrowser] Starting stealth driver...")
            options = uc.ChromeOptions()
            options.add_argument('--window-size=1920,1080')
            if self.headless:
                options.add_argument('--headless=new')
            # Force version 145 to match system version found in logs
            self.driver = uc.Chrome(options=options, version_main=145)

    async def execute(self, action: str, **kwargs: Any) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._execute_sync, action, kwargs)

    def _execute_sync(self, action: str, kwargs: Dict[str, Any]) -> str:
        self._ensure_browser()
        logger.info(f"[HybridBrowser] Action: {action}")
        
        try:
            if action in ["navigate", "open"]:
                url = kwargs.get("url")
                if not url: return "Error: No URL provided."
                self.driver.get(url)
                return f"Navigated to {url}"
            
            elif action == "click":
                selector = kwargs.get("selector")
                x, y = kwargs.get("x"), kwargs.get("y")
                
                if selector:
                    element = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    element.click()
                    return f"Clicked element (selector): {selector}"
                elif x is not None and y is not None:
                    # Coordinate-based click (normalized 0-1000)
                    window_size = self.driver.get_window_size()
                    real_x = int(x * window_size['width'] / 1000)
                    real_y = int(y * window_size['height'] / 1000)
                    from selenium.webdriver.common.action_chains import ActionChains
                    actions = ActionChains(self.driver)
                    actions.move_by_offset(real_x, real_y).click().perform()
                    # Reset offset for next call
                    actions.move_by_offset(-real_x, -real_y).perform()
                    return f"Clicked at coordinates: ({real_x}, {real_y})"
            
            elif action == "type":
                selector = kwargs.get("selector")
                text = kwargs.get("text")
                if not text: return "Error: No text provided."
                
                if selector:
                    element = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    element.clear()
                    element.send_keys(text)
                    return f"Typed '{text}' into {selector}"
                else:
                    # Type blindly (e.g. after a click)
                    from selenium.webdriver.common.action_chains import ActionChains
                    actions = ActionChains(self.driver)
                    actions.send_keys(text).perform()
                    return f"Typed blindly: '{text}'"

            elif action == "screenshot":
                label = kwargs.get("label", "snap")
                # Ensure memory dir exists
                self.memory.screenshots_dir.mkdir(parents=True, exist_ok=True)
                path = self.memory.screenshots_dir / f"{label}_{int(time.time())}.png"
                self.driver.save_screenshot(str(path))
                return str(path) # Return path for the VisionEngine to use
                
            return f"Action {action} completed."
        except Exception as e:
            logger.error(f"[HybridBrowser] Error: {e}")
            return f"Error: {e}"

    def __del__(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
