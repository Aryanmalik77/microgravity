import tkinter as tk
from threading import Thread
import time
from typing import Optional

class HUDOverlay:
    """
    A transparent, always-on-top overlay to display agent status and intent.
    """
    def __init__(self):
        self.root = None
        self.label_goal = None
        self.label_action = None
        self.label_status = None
        self.label_step = None
        
        self.goal_text = "Goal: Initializing..."
        self.action_text = "Action: Idle"
        self.status_text = "Live Stream: Offline"
        self.step_text = "Step: --"
        self.status_color = "#FF4444"
        
        self._thread = Thread(target=self._run_tk, daemon=True)
        self._thread.start()
        
    def _run_tk(self):
        try:
            self.root = tk.Tk()
            self.root.title("Agentic OS HUD")
            
            # Make transparent and always on top
            self.root.attributes("-topmost", True)
            self.root.attributes("-transparentcolor", "black")
            self.root.overrideredirect(True) # Remove title bar
            
            # Position at the top right
            screen_width = self.root.winfo_screenwidth()
            self.root.geometry(f"420x180+{screen_width - 440}+20")
            
            self.root.config(bg="black")
            
            # Status Labels
            font_style = ("Consolas", 12, "bold")
            
            self.label_goal = tk.Label(self.root, text=self.goal_text, fg="#00FF00", bg="black", font=font_style, wraplength=380, justify="left")
            self.label_goal.pack(anchor="w", padx=10, pady=2)
            
            self.label_action = tk.Label(self.root, text=self.action_text, fg="#00FFFF", bg="black", font=font_style, wraplength=380, justify="left")
            self.label_action.pack(anchor="w", padx=10, pady=2)
            
            self.label_status = tk.Label(self.root, text=self.status_text, fg="#FF4444", bg="black", font=font_style)
            self.label_status.pack(anchor="w", padx=10, pady=2)
            
            self.label_step = tk.Label(self.root, text=self.step_text, fg="#FFD700", bg="black", font=("Consolas", 10), wraplength=400, justify="left")
            self.label_step.pack(anchor="w", padx=10, pady=2)
            
            self._update_loop()
            self.root.mainloop()
        except Exception as e:
            print(f"[HUD] Initialization failed: {e}")

    def _update_loop(self):
        if self.root:
            try:
                self.label_goal.config(text=self.goal_text)
                self.label_action.config(text=self.action_text)
                self.label_status.config(text=self.status_text, fg=self.status_color)
                self.label_step.config(text=self.step_text)
                self.root.after(100, self._update_loop)
            except:
                pass

    def update_goal(self, text):
        self.goal_text = f"Goal: {text}"

    def update_action(self, text):
        self.action_text = f"Action: {text}"

    def update_status(self, is_streaming, fallback_active=False):
        if is_streaming:
            status = "ONLINE"
            self.status_color = "#00FF00"  # Green
        elif fallback_active:
            status = "Static VLM Active"
            self.status_color = "#FFA500"  # Orange
        else:
            status = "Offline"
            self.status_color = "#FF4444"  # Red
        self.status_text = f"Live Stream: {status}"

    def update_step(self, step_num: int, reasoning: str = ""):
        """Updates the step display with current step number and planner reasoning."""
        if reasoning:
            self.step_text = f"Step {step_num}: {reasoning[:60]}"
        else:
            self.step_text = f"Step {step_num}"
        
    def stop(self):
        if self.root:
            self.root.quit()
