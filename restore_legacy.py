import shutil
from pathlib import Path

microgravity_path = Path.home() / ".microgravity"
nanobot_path = Path.home() / ".nanobot"

if microgravity_path.exists():
    if not nanobot_path.exists():
        print(f"Copying {microgravity_path} to {nanobot_path} for legacy support")
        shutil.copytree(str(microgravity_path), str(nanobot_path))
    else:
        print(f"Legacy {nanobot_path} already exists.")
else:
    print(f"{microgravity_path} does not exist.")
