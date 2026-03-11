import os

def replace_in_file(file_path, old_str, new_str):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Simple string replacement for imports
        # Be careful not to replace things like "nanobot" in comments that should stay, 
        # but for rebranding, almost all should change.
        # We target "from microgravity", "import microgravity", "microgravity."
        
        new_content = content.replace('from microgravity', f'from {new_str}')
        new_content = new_content.replace('import microgravity', f'import {new_str}')
        new_content = new_content.replace('microgravity.', f'{new_str}.')
        
        if new_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
    return False

root_dir = r"C:\Users\HP\Downloads\micro gravity - Copy"
rebrand_to = "microgravity"

count = 0
for root, dirs, files in os.walk(root_dir):
    # Skip .git and venv
    if '.git' in dirs:
        dirs.remove('.git')
    if 'venv' in dirs:
        dirs.remove('venv')
        
    for file in files:
        if file.endswith(('.py', '.ts', '.js', '.md', '.json', '.yml', '.yaml', '.toml', 'Dockerfile')):
            if replace_in_file(os.path.join(root, file), 'nanobot', rebrand_to):
                count += 1

print(f"Updated {count} files.")
