import os
import shutil
from pathlib import Path

base_dir = Path(r"C:\Users\HP\Downloads\micro gravity - Copy\legacy\frameworks")
microgravity_dir = base_dir / "microgravity"

# Folders that belong inside the microgravity package
target_folders = [
    "agent", "bridge", "bus", "channels", "cli", "config", "cron", 
    "heartbeat", "providers", "session", "skills", "src", "swarm", 
    "templates", "tests", "utils", "agent_memory", "ui_agent_engine"
]

# Files that belong inside the microgravity package
target_files = ["__init__.py", "__main__.py"]

if not microgravity_dir.exists():
    microgravity_dir.mkdir()

for folder in target_folders:
    src = base_dir / folder
    dst = microgravity_dir / folder
    if src.exists() and src.is_dir() and folder != "microgravity" and folder != "nanobot":
        if dst.exists():
            print(f"Destination {dst} already exists, skipping...")
        else:
            print(f"Moving {src} to {dst}")
            shutil.move(str(src), str(dst))

for file in target_files:
    src = base_dir / file
    dst = microgravity_dir / file
    if src.exists() and src.is_file():
        if dst.exists():
             print(f"Destination {dst} already exists, skipping...")
        else:
            print(f"Moving {src} to {dst}")
            shutil.move(str(src), str(dst))

# Handle the existing 'nanobot' directory if it exists (it might be empty or contain old stuff)
old_nanobot = base_dir / "nanobot"
if old_microgravity.exists():
    print(f"Removing old nanobot directory {old_nanobot}")
    shutil.rmtree(str(old_nanobot))

print("Done fixing structure and renaming to microgravity.")
