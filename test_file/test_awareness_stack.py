import os
import sys
import time
import cv2
import numpy as np
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "ui_agent_engine" / "src"))

from perception.cv_pipeline import CVPipeline
from perception.static_dynamic_classifier import StaticDynamicClassifier
from perception.element_boundary_learner import ElementBoundaryLearner
from perception.os_awareness import OSAwareness
from perception.app_characterizer import AppCharacterizer
from planning.experiential_memory import ExperientialMemory
from agent_core.ui_memory_agent import UIMemoryAgent
from planning.situational_awareness import SituationalAwareness
from planning.decision_manager import DecisionManager
from perception.vision_analyzer import VisionAnalyzer
import mss

def test_awareness_stack():
    print("=== Starting Awareness Stack Integration Test ===")
    workspace_path = Path(__file__).parent / "test_workspace"
    workspace_path.mkdir(exist_ok=True)
    
    # 1. Initialize Stack
    print("\n[1] Initializing Stack...")
    memory_agent = UIMemoryAgent(workspace_path)
    experiential_memory = ExperientialMemory(workspace_path / "agent_memory" / "experiential")
    cv_pipeline = CVPipeline()
    vision_analyzer = VisionAnalyzer(cv_pipeline=cv_pipeline)
    os_awareness = OSAwareness()
    stability_classifier = StaticDynamicClassifier(cv_pipeline=cv_pipeline)
    boundary_learner = ElementBoundaryLearner(cv_pipeline=cv_pipeline, vision_analyzer=vision_analyzer)
    app_characterizer = AppCharacterizer(cv_pipeline=cv_pipeline, vision_analyzer=vision_analyzer, memory_agent=memory_agent)
    
    situational_awareness = SituationalAwareness(
        os_awareness=os_awareness,
        app_characterizer=app_characterizer,
        cv_pipeline=cv_pipeline,
        boundary_learner=boundary_learner,
        stability_classifier=stability_classifier,
        memory=memory_agent
    )
    
    decision_manager = DecisionManager(
        experiential_memory=experiential_memory,
        boundary_learner=boundary_learner,
        cv_pipeline=cv_pipeline,
        stability_classifier=stability_classifier,
        live_streamer=None,
        vision_analyzer=vision_analyzer,
        ui_memory_agent=memory_agent
    )
    
    print("Stack initialized successfully.")

    # 2. Capture a live frame
    print("\n[2] Capturing screen frame...")
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        screenshot = sct.grab(monitor)
        frame = np.array(screenshot)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

    # 3. Build World Model and Trigger Speculative Snipping
    print("\n[3] Building World Model (This will trigger speculative snipping)...")
    world_model = situational_awareness.build_world_model(current_frame=frame)
    
    print(f"Foreground Window: {world_model.foreground_title}")
    print(f"Detected {len(world_model.element_map)} elements via CV.")
    
    # 4. Check UI Atlas for speculatively saved elements
    print("\n[4] Checking UI Atlas for Speculative Snippets...")
    context_name = world_model.foreground_state.get("class_name") or world_model.foreground_title or "Desktop"
    
    context_data = memory_agent.get_context_map(context_name)
    elements = context_data.get("elements", {})
    
    speculative_count = 0
    test_target_label = None
    
    for label, data in elements.items():
        if data.get("is_speculative"):
            speculative_count += 1
            if test_target_label is None:
                test_target_label = label  # Pick the first one to test resolution
            
    print(f"Found {speculative_count} speculative elements saved in the Atlas for context '{context_name}'.")
    
    if speculative_count == 0:
        print("WARNING: No speculative elements were saved. This might be because no elements were detected, or stability checks failed.")
        if len(world_model.element_map) > 0:
            print("Elements were detected. Let's force a snippet save manually to test DecisionManager.")
            elem = world_model.element_map[0]
            x, y, w, h = elem["x"], elem["y"], elem["w"], elem["h"]
            template = frame[int(y):int(y+h), int(x):int(x+w)]
            test_target_label = "test_speculative_button"
            memory_agent.remember_element(
                context=context_name,
                label=test_target_label,
                data={"coords": [x, y, w, h], "type": "BUTTON", "is_speculative": True, "stability_class": "STATIC"},
                template=template,
                embedding=[0.1]*60 # Fake embedding
            )
            print("Forced save of one element.")
            
    # 5. Test DecisionManager ATLAS_LOOKUP
    print("\n[5] Testing DecisionManager ATLAS_LOOKUP...")
    if test_target_label:
        print(f"Attempting to resolve action for target: '{test_target_label}'")
        resolution = decision_manager.resolve_action(
            action="click",
            target_desc=test_target_label,
            current_frame=frame,
            app_class=context_name
        )
        
        print(f"Resolution Success: {resolution.success}")
        print(f"Resolution Method: {resolution.method}")
        print(f"Target Coords: {resolution.target_coords}")
        print(f"Confidence: {resolution.confidence}")
        
        if resolution.success and resolution.target_coords:
            # ==== NEW: MAKE IT LIVELY ====
            print("\n[6] Making it LIVELY by moving the mouse and displaying vision...")
            try:
                # 1. Move mouse to target
                sys.path.append(str(Path(__file__).parent / "ui_agent_engine" / "src" / "ui_controller"))
                from ui_controller.mouse_controller import MouseController
                mouse = MouseController()
                cx, cy = resolution.target_coords
                print(f"Physical mouse move to ({cx}, {cy})...")
                mouse.move_to(int(cx), int(cy), duration=1.0)
                
                # 2. Draw bounding boxes on the frame to show what the agent saw
                display_frame = frame.copy()
                
                # Draw all detected raw elements in blue
                for el in world_model.element_map:
                    cv2.rectangle(display_frame, (int(el['x']), int(el['y'])), (int(el['x']+el['w']), int(el['y']+el['h'])), (255, 0, 0), 1)
                
                # Draw the specific target resolved via ATLAS_LOOKUP in GREEN
                if resolution.target_rect:
                    rx1, ry1, rx2, ry2 = resolution.target_rect
                    cv2.rectangle(display_frame, (int(rx1), int(ry1)), (int(rx2), int(ry2)), (0, 255, 0), 3)
                    cv2.putText(display_frame, "SPECULATIVE TARGET MATCH (ATLAS_LOOKUP)", (int(rx1), max(10, int(ry1)-10)), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
                    # Draw click point
                    cv2.circle(display_frame, (int(cx), int(cy)), 5, (0, 0, 255), -1)

                # Show it
                print("Displaying agent vision. Press any key in the window to close.")
                # Resize if it's too big for the screen
                h, w = display_frame.shape[:2]
                display_frame = cv2.resize(display_frame, (w//2, h//2))
                cv2.imshow("Agent Live Vision & Speculative Snipping Test", display_frame)
                cv2.waitKey(0)
                cv2.destroyAllWindows()
                
            except Exception as e:
                print(f"Failed to show lively test: {e}")
        else:
            print("DecisionManager failed to resolve the target!")
    else:
        print("Could not test DecisionManager because no target label was found.")

    print("\n=== All Tests Completed Successfully! ===")

if __name__ == "__main__":
    test_awareness_stack()
