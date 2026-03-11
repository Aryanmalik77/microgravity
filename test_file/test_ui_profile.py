import asyncio
import os
import sys
import shutil
from pathlib import Path

# Add project root and src to path
project_root = Path(r"C:\Users\HP\Downloads\micro gravity - Copy")
sys.path.insert(0, str(project_root))

from src.memory.kernel import MemoryKernel
from src.kernel.loop import KernelLoop

async def test_ui_profile_database():
    print("Testing UI Profile Database...\n")
    
    # 1. Setup mock storage
    test_storage_dir = project_root / "test_storage"
    if test_storage_dir.exists():
        shutil.rmtree(test_storage_dir)
    
    kernel = MemoryKernel(test_storage_dir)
    profile_store = kernel.profiles
    
    # 2. Test Temporary Session Profiles
    print("--- Short-Term Memory Test ---")
    session_id = "task_nav_123"
    temp_state = {"current_url": "https://github.com", "found_buttons": ["Login", "Signup"]}
    
    profile_store.save_session_profile(session_id, temp_state)
    retrieved_state = profile_store.get_session_profile(session_id)
    
    assert retrieved_state == temp_state, "Retrieve session state failed."
    print("PASS: Saved and retrieved temporary session profile.")
    
    profile_store.clear_session(session_id)
    cleared_state = profile_store.get_session_profile(session_id)
    assert cleared_state == {}, "Clear session state failed."
    print("PASS: Flushed temporary session profile.")
    
    # 3. Test Permanent Macros
    print("\n--- Long-Term Memory (Macro) Test ---")
    macro_name = "Export Daily Sales"
    macro_sequence = [
        {"action": "click", "target": "reports_tab"},
        {"action": "click", "target": "export_button"},
        {"action": "type", "target": "filename_input", "value": "daily_sales.csv"},
        {"action": "click", "target": "confirm_button"}
    ]
    
    profile_store.save_permanent_macro(macro_name, macro_sequence)
    
    # Find macro using the heuristic task matcher
    matched_macro = profile_store.find_macro_for_task("Please export daily sales for me")
    
    assert matched_macro is not None, "Failed to find matching macro."
    assert matched_macro["macro_name"] == macro_name, "Matched wrong macro."
    assert matched_macro["sequence"] == macro_sequence, "Macro sequence corrupted."
    
    print(f"PASS: Saved and retrieved permanent macro '{macro_name}'.")
    
    # Cleanup - close LMDB env first to release file locks on Windows
    if hasattr(kernel, 'env') and kernel.env:
        kernel.env.close()
    shutil.rmtree(test_storage_dir, ignore_errors=True)
    print("\nAll UI Profile Database Tests Passed Successfully!")

if __name__ == "__main__":
    asyncio.run(test_ui_profile_database())
