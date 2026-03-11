import os
import shutil
from pathlib import Path

base_dir = Path(r"C:\Users\HP\Downloads\micro gravity - Copy\legacy\frameworks")
nanobot_dir = base_dir / "nanobot"

# Folders that belong inside the nanobot package
target_folders = [
    "agent", "bridge", "bus", "channels", "cli", "config", "cron", 
    "heartbeat", "providers", "session", "skills", "src", "swarm", 
    "templates", "tests", "utils", "agent_memory", "ui_agent_engine"
]

# Files that belong inside the nanobot package
target_files = ["__init__.py", "__main__.py"]

if not nanobot_dir.exists():
    nanobot_dir.mkdir()

for folder in target_folders:
    src = base_dir / folder
    dst = nanobot_dir / folder
    if src.exists() and src.is_dir() and folder != "nanobot":
        if dst.exists():
            print(f"Destination {dst} already exists, skipping...")
        else:
            print(f"Moving {src} to {dst}")
            shutil.move(str(src), str(dst))

for file in target_files:
    src = base_dir / file
    dst = nanobot_dir / file
    if src.exists() and src.is_file():
        if dst.exists():
             print(f"Destination {dst} already exists, skipping...")
        else:
            print(f"Moving {src} to {dst}")
            shutil.move(str(src), str(dst))

print("Done fixing structure.")
