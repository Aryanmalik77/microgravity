import mss
import mss.tools
from PIL import Image
import os
import time
from typing import Optional, Tuple, List
import ctypes
import win32gui
import win32ui
import win32con
from pathlib import Path
from loguru import logger

class WindowObserver:
    """
    Captures specific application windows (even if they are in the background)
    using the Windows Graphics Device Interface (GDI) and PrintWindow API.
    """
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_window_titles(self) -> List[str]:
        """Returns a list of all visible window titles."""
        titles = []
        def enum_windows_proc(hwnd, lParam):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                titles.append(win32gui.GetWindowText(hwnd))
            return True
        win32gui.EnumWindows(enum_windows_proc, None)
        return titles

    def capture_window_by_title(self, window_title: str, filename: Optional[str] = None) -> Optional[str]:
        """
        Takes a screenshot of the specified window's image buffer.
        """
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1) # PROCESS_SYSTEM_DPI_AWARE
        except:
            pass

        hwnd = win32gui.FindWindow(None, window_title)
        actual_title = window_title
        
        if not hwnd:
            for title in self.get_window_titles():
                if window_title.lower() in title.lower():
                    hwnd = win32gui.FindWindow(None, title)
                    actual_title = title
                    break
            
            if not hwnd:
                logger.warning(f"[WindowObserver] Error: Window '{window_title}' not found.")
                return None

        if win32gui.IsIconic(hwnd):
           win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
           time.sleep(0.1)

        if filename is None:
            filename = f"window_{int(time.time()*1000)}.png"
        filepath = self.output_dir / filename

        left, top, right, bottom = win32gui.GetClientRect(hwnd)
        width = right - left
        height = bottom - top

        if width <= 0 or height <= 0:
            logger.error(f"[WindowObserver] Error: Window '{actual_title}' has invalid dimensions.")
            return None

        hwndDC = win32gui.GetWindowDC(hwnd)
        mfcDC  = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()

        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
        saveDC.SelectObject(saveBitMap)

        # PW_RENDERFULLCONTENT = 3, PW_CLIENTONLY = 1
        result = ctypes.windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 3 | 1)

        bmpinfo = saveBitMap.GetInfo()
        bmpstr = saveBitMap.GetBitmapBits(True)

        if len(bmpstr) > 0 and result != 0:
             im = Image.frombuffer(
                 'RGB',
                 (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                 bmpstr, 'raw', 'BGRX', 0, 1)
             im.save(str(filepath))
             logger.info(f"[WindowObserver] Captured window buffer '{actual_title}' to {filepath}")
        else:
             logger.error(f"[WindowObserver] PrintWindow failed or returned empty buffer for '{actual_title}'.")
             filepath = None

        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwndDC)

        return str(filepath) if filepath else None

class ScreenObserver:
    """
    Handles fast screenshot capture using mss.
    """
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        import threading
        self._thread_local = threading.local()
        
    @property
    def sct(self):
        """Thread-local mss instance."""
        if not hasattr(self._thread_local, 'sct'):
            self._thread_local.sct = mss.mss()
        return self._thread_local.sct
        
    def capture(self, filename: Optional[str] = None, region: Optional[Tuple[int, int, int, int]] = None) -> Optional[str]:
        """
        Captures the screen or a specific region.
        Region is (left, top, width, height).
        """
        if filename is None:
            filename = f"screenshot_{int(time.time()*1000)}.png"
            
        filepath = self.output_dir / filename
        
        monitor = self.sct.monitors[1]
        if region:
            monitor = {
                "left": monitor["left"] + region[0],
                "top": monitor["top"] + region[1],
                "width": region[2],
                "height": region[3]
            }

        try:
            screenshot = self.sct.grab(monitor)
            mss.tools.to_png(screenshot.rgb, screenshot.size, output=str(filepath))
            logger.info(f"[ScreenObserver] Captured screenshot to {filepath}")
            return str(filepath)
        except Exception as e:
            logger.error(f"[ScreenObserver] Error during screen capture: {e}")
            return None
        
    def capture_as_pil(self, region: Optional[Tuple[int, int, int, int]] = None) -> Image.Image:
        """Captures the screen and returns a PIL Image."""
        monitor = self.sct.monitors[1]
        if region:
            monitor = {
                "left": monitor["left"] + region[0],
                "top": monitor["top"] + region[1],
                "width": region[2],
                "height": region[3]
            }
            
        screenshot = self.sct.grab(monitor)
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        return img

    def capture_as_cv2(self, region: Optional[Tuple[int, int, int, int]] = None):
        """Captures the screen and returns a numpy array (BGR)."""
        import numpy as np
        import cv2
        monitor = self.sct.monitors[1]
        if region:
            monitor = {
                "left": monitor["left"] + region[0],
                "top": monitor["top"] + region[1],
                "width": region[2],
                "height": region[3]
            }
        screenshot = self.sct.grab(monitor)
        img = np.array(screenshot)
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
