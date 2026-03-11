import ctypes
import pyautogui
import mss
from PIL import ImageGrab

def get_screen_size_info():
    """Prints DPI and screen size info from different sources."""
    print("--- DPI & Screen Size Diagnosis ---")
    
    # OS Level Resolution
    user32 = ctypes.windll.user32
    screensize = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    print(f"OS Reports (user32): {screensize[0]} x {screensize[1]}")
    
    # PyAutoGUI (Logical/Physical depending on awareness)
    pa_size = pyautogui.size()
    print(f"PyAutoGUI Reports: {pa_size}")
    
    # ImageGrab (Logical if not aware)
    ig_img = ImageGrab.grab()
    print(f"ImageGrab Reports: {ig_img.size}")
    
    # MSS (DPI Aware - usually physical)
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        print(f"MSS Reports (Monitor 1): {monitor['width']} x {monitor['height']} (Top: {monitor['top']}, Left: {monitor['left']})")
    
    # Calculate Scaling
    if screensize[0] != monitor['width']:
        scaling = (monitor['width'] / screensize[0]) * 100
        print(f"Detected Scaling (MSS vs OS): {scaling:.1f}%")
    else:
        print("Scaling seems to be 100% (MSS matching OS)")

if __name__ == "__main__":
    print("1. Diagnosis BEFORE forcing awareness:")
    get_screen_size_info()
    
    print("\n2. Diagnosis AFTER forcing awareness (ProcessAwareness=2):")
    try:
        # Shcore.SetProcessDpiAwareness(2) -> PROCESS_PER_MONITOR_DPI_AWARE
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception as e:
        print(f"Could not set DPI awareness: {e}")
        
    get_screen_size_info()
