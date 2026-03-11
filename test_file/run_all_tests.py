"""
MICROGRAVITY AGENTIC OS - Full Test Suite Runner
Runs all architectural tests sequentially and reports results.
"""
import subprocess
import sys
import os
import time
from pathlib import Path

# API keys are now handled internally by components via load_config()

TEST_SUITE = [
    ("Phase 1: Task Classification",    test_dir / "test_task_classification.py"),
    ("Phase 2: UI Profile Database",    test_dir / "test_ui_profile.py"),
    ("Phase 3: Safety Interceptor",     test_dir / "test_interceptor.py"),
    ("Phase 4: Auto-Tuning Loop",       test_dir / "test_autotune.py"),
    ("Phase 5: Scenario Modeling",      test_dir / "test_scenarios.py"),
    ("Phase 6: Full Integration",       test_dir / "test_integration_master.py"),
]

def run_test(name, script_path):
    print(f"\n{'='*60}")
    print(f"  RUNNING: {name}")
    print(f"  Script:  {script_path.name}")
    print(f"{'='*60}")
    
    start = time.time()
    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(project_root),
        capture_output=True,
        text=True,
        timeout=60
    )
    elapsed = time.time() - start
    
    passed = result.returncode == 0
    status = "PASS" if passed else "FAIL"
    
    # Print condensed output
    output = result.stdout + result.stderr
    # Show last 15 meaningful lines
    lines = [l for l in output.strip().split('\n') if l.strip()]
    for line in lines[-15:]:
        print(f"  | {line}")
    
    print(f"\n  Result: [{status}] in {elapsed:.1f}s")
    return passed, elapsed

def main():
    print("="*60)
    print("  MICROGRAVITY AGENTIC OS - FULL TEST SUITE")
    print("="*60)
    
    results = []
    total_start = time.time()
    
    for name, script in TEST_SUITE:
        try:
            passed, elapsed = run_test(name, script)
            results.append((name, passed, elapsed))
        except subprocess.TimeoutExpired:
            print(f"  Result: [TIMEOUT] after 60s")
            results.append((name, False, 60.0))
        except Exception as e:
            print(f"  Result: [ERROR] {e}")
            results.append((name, False, 0.0))
    
    total_time = time.time() - total_start
    
    # Final Report
    print(f"\n\n{'='*60}")
    print("  FINAL REPORT")
    print(f"{'='*60}")
    
    passed_count = sum(1 for _, p, _ in results if p)
    total_count = len(results)
    
    for name, passed, elapsed in results:
        icon = "[OK]" if passed else "[!!]"
        status_text = "PASS" if passed else "FAIL"
        print(f"  {icon} {name:<40} {status_text:>6}  ({elapsed:.1f}s)")
    
    print(f"\n  Total: {passed_count}/{total_count} passed in {total_time:.1f}s")
    print(f"{'='*60}")
    
    sys.exit(0 if passed_count == total_count else 1)

if __name__ == "__main__":
    main()
