import os
import sys
from dotenv import load_dotenv

# Add parent to path for relative import execution
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from src.perception.spatial_understanding.spatial_tool import SpatialUnderstandingTool

def main():
    from microgravity.config.loader import load_config
    api_key = load_config().providers.gemini.api_key
    tool = SpatialUnderstandingTool(api_key=api_key)

    images = [
        r"c:\Users\HP\Downloads\photo_6116080631654584865_y.jpg",
        r"c:\Users\HP\Downloads\photo_6116080631654584864_x.jpg",
        r"c:\Users\HP\Downloads\photo_6116080631654584863_x.jpg",
        r"c:\Users\HP\Downloads\photo_6116080631654584862_x.jpg"
    ]

    for img in images:
        if not os.path.exists(img): continue
            
        print(f"\n--- {os.path.basename(img)} ---")
        try:
            res_pt = tool.execute(img, "openclaw", "points", None)
            print("Coordinates for 'openclaw' (Points):", res_pt.get("results"))
        except Exception as e:
            pass
            
        try:
            res_bbox = tool.execute(img, "openclaw chat", "2d_bounding_boxes", None)
            print("Coordinates for 'openclaw chat' (2D Bboxes):", res_bbox.get("results"))
        except Exception as e:
            pass

if __name__ == "__main__":
    main()
