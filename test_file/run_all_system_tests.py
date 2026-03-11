"""
MICROGRAVITY AGENTIC OS - COMPLETE SYSTEM TEST SUITE
Runs Architecture + Swarm + UI Agent tests sequentially.
"""
import subprocess
import sys
import os
import time
from pathlib import Path

project_root = Path(r"C:\Users\HP\Downloads\micro gravity - Copy")
test_dir = project_root / "test_file"
scripts_dir = project_root / "scripts"

# API keys are now handled internally by components via load_config()

# =====================================================================
# TEST REGISTRY: All tests organized by system layer
# =====================================================================
TEST_SUITE = [
    # --- Layer 1: Architecture (Phase 1-4) ---
    ("ARCH | Task Classification",      test_dir / "test_task_classification.py"),
    ("ARCH | UI Profile Database",      test_dir / "test_ui_profile.py"),
    ("ARCH | Safety Interceptor",       test_dir / "test_interceptor.py"),
    ("ARCH | Auto-Tuning Loop",         test_dir / "test_autotune.py"),
    
    # --- Layer 2: Scenario Modeling ---
    ("SCEN | Scenario Modeling",        test_dir / "test_scenarios.py"),
    ("SCEN | Full Integration",         test_dir / "test_integration_master.py"),
    
    # --- Layer 3: Swarm Architecture ---
    ("SWRM | Swarm Architecture",       scripts_dir / "verify_swarm.py"),
    ("SWRM | Swarm Simple",            test_dir / "test_swarm_simple.py"),
    
    # --- Layer 4: UI Agent ---
    ("UIAG | UI Agent Prototype",       test_dir / "test_ui_agent.py"),
]

def run_test(name, script_path, timeout=60):
    """Execute a single test script and capture its result."""
    if not script_path.exists():
        return False, 0.0, f"Script not found: {script_path}"
    
    print(f"\n{'='*60}")
    print(f"  RUNNING: {name}")
    print(f"  Script:  {script_path.name}")
    print(f"{'='*60}")
    
    start = time.time()
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=timeout
        )
        elapsed = time.time() - start
        passed = result.returncode == 0
        
        # Print condensed output (last 15 meaningful lines)
        output = result.stdout + result.stderr
        lines = [l for l in output.strip().split('\n') if l.strip()]
        for line in lines[-15:]:
            print(f"  | {line[:100]}")
        
        status = "PASS" if passed else "FAIL"
        print(f"\n  Result: [{status}] in {elapsed:.1f}s")
        return passed, elapsed, ""
        
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        print(f"\n  Result: [TIMEOUT] after {timeout}s")
        return False, elapsed, "TIMEOUT"
    except Exception as e:
        elapsed = time.time() - start
        print(f"\n  Result: [ERROR] {e}")
        return False, elapsed, str(e)

def main():
    print("=" * 60)
    print("  MICROGRAVITY AGENTIC OS")
    print("  COMPLETE SYSTEM TEST SUITE")
    print("  Architecture + Swarm + UI Agent")
    print("=" * 60)
    
    results = []
    total_start = time.time()
    
    for name, script in TEST_SUITE:
        passed, elapsed, error = run_test(name, script)
        results.append((name, passed, elapsed, error))
    
    total_time = time.time() - total_start
    
    # =====================================================================
    # FINAL REPORT
    # =====================================================================
    print(f"\n\n{'='*60}")
    print("  FINAL REPORT")
    print(f"{'='*60}")
    
    layer_results = {}
    for name, passed, elapsed, error in results:
        layer = name.split("|")[0].strip()
        if layer not in layer_results:
            layer_results[layer] = {"passed": 0, "total": 0}
        layer_results[layer]["total"] += 1
        if passed:
            layer_results[layer]["passed"] += 1
    
    # Print per-test results
    current_layer = ""
    for name, passed, elapsed, error in results:
        layer = name.split("|")[0].strip()
        test_name = name.split("|")[1].strip()
        
        if layer != current_layer:
            current_layer = layer
            layer_label = {"ARCH": "Architecture", "SCEN": "Scenarios", "SWRM": "Swarm", "UIAG": "UI Agent"}.get(layer, layer)
            print(f"\n  --- {layer_label} ---")
        
        icon = "[OK]" if passed else "[!!]"
        status_text = "PASS" if passed else "FAIL"
        extra = f" ({error})" if error else ""
        print(f"  {icon} {test_name:<35} {status_text:>6}  ({elapsed:.1f}s){extra}")
    
    # Summary
    passed_count = sum(1 for _, p, _, _ in results if p)
    total_count = len(results)
    
    print(f"\n  {'='*56}")
    for layer, counts in layer_results.items():
        layer_label = {"ARCH": "Architecture", "SCEN": "Scenarios", "SWRM": "Swarm", "UIAG": "UI Agent"}.get(layer, layer)
        print(f"  {layer_label:<20} {counts['passed']}/{counts['total']} passed")
    
    print(f"\n  TOTAL: {passed_count}/{total_count} passed in {total_time:.1f}s")
    print(f"{'='*60}")
    
    sys.exit(0 if passed_count == total_count else 1)

if __name__ == "__main__":
    main()
