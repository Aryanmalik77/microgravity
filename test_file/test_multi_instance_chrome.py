import time
import os
import sys
import subprocess

# Add project root to path
sys.path.append(os.path.join(os.getcwd(), "ui_agent_engine", "src"))
sys.path.append(os.path.join(os.getcwd(), "ui_agent_engine"))

from agent_core.ui_agent import UIAgent
from ui_controller.window_manager import WindowManager

def test_multi_instance_focus():
    wm = WindowManager()
    agent = UIAgent()
    
    print("[Test] Opening 3 Chrome windows...")
    for i in range(3):
        subprocess.Popen(["start", "chrome", "--new-window", "https://www.google.com"], shell=True)
        time.sleep(3)
    
    print("[Test] Waiting for windows to initialize...")
    time.sleep(5)

    print("[Test] Scanning all windows...")
    chrome_hwnds = []
    agent.os_awareness.scan_all_windows()
    
    # Debug: Print all found windows
    print(f"[Test] Found {len(agent.os_awareness.window_ledger)} windows in total.")
    for hwnd, ws in agent.os_awareness.window_ledger.items():
        if "chrome" in ws.process_name.lower() or "chrome" in ws.title.lower():
            print(f"  MATCH: HWND {hwnd} | App: {ws.process_name} | Title: {ws.title}")
            wm.minimize(ws.hwnd)
            chrome_hwnds.append(ws.hwnd)

    if not chrome_hwnds:
        # One last try with raw Win32 enumeration for debug
        import win32gui
        def callback(hwnd, extra):
            title = win32gui.GetWindowText(hwnd)
            if "google" in title.lower() or "chrome" in title.lower():
                extra.append(hwnd)
        
        extra = []
        win32gui.EnumWindows(callback, extra)
        print(f"[Test] Raw Win32 search found {len(extra)} potential windows: {extra}")
        
        print("[Test] FAILED: No Chrome windows found in OSAwareness ledger.")
        return

    target_hwnd = chrome_hwnds[0]
    print(f"[Test] Instructing agent to focus specific HWND: {target_hwnd}")
    
    # We simulate a situation where the planner decided to use focus_window
    action = {
        "action": "focus_window",
        "hwnd": target_hwnd,
        "reasoning": "Restoring specific Chrome instance to avoid taskbar disambiguation."
    }
    
    print("[Test] Executing focus_window action...")
    agent._execute_action(action)
    
    time.sleep(2)
    
    # Verify
    import win32gui
    fg_hwnd = win32gui.GetForegroundWindow()
    if fg_hwnd == target_hwnd:
        print(f"[Test] SUCCESS: Window {target_hwnd} is now in foreground.")
    else:
        print(f"[Test] FAILURE: Expected {target_hwnd} in foreground, but found {fg_hwnd}.")

if __name__ == "__main__":
    test_multi_instance_focus()
