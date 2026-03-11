"""
MICROGRAVITY - Introspection and Swarm Integration Test Suite
Tests the IntrospectionEngine + fixes Swarm import paths + runs everything.
"""
import subprocess
import sys
import os
import time
from pathlib import Path

project_root = Path(r"C:\Users\HP\Downloads\micro gravity - Copy")
test_dir = project_root / "test_file"
scripts_dir = project_root / "scripts"
nanobot_root = Path(r"C:\Users\HP\Downloads\micro gravity\nanobot")

# API keys are now handled internally by components via load_config()

# =============================================================
# INLINE TEST: Introspection Engine
# =============================================================
def test_introspection():
    """Test the IntrospectionEngine's self-inspection capabilities."""
    sys.path.insert(0, str(project_root))
    from src.kernel.introspection import IntrospectionEngine
    from src.kernel.interceptor import PowerLevel
    
    print("=" * 60)
    print("  INTROSPECTION ENGINE TEST")
    print("=" * 60)
    
    engine = IntrospectionEngine()
    
    # --- Test 1: State Registration ---
    print("\n--- Test 1: System State Registration ---")
    engine.register_system_state("power_level", PowerLevel.EXECUTOR.value)
    engine.register_system_state("zoom_level", 1.5)
    engine.register_system_state("llm_provider", "gemini-2.5-flash")
    engine.register_system_state("consecutive_failures", 0)
    engine.register_system_state("screenshots_taken", 3)
    engine.register_system_state("live_streamer_connected", False)
    engine.register_system_state("task_completed", True)
    engine.register_system_state("task_description", "Click the submit button")
    engine.register_system_state("blocked_actions", [])
    engine.register_system_state("safety_log_count", 0)
    engine.register_system_state("actions_attempted", ["click"])
    engine.register_system_state("last_action_attempted", True)
    
    state = engine.inspect_state()
    assert "power_level" in state
    assert state["zoom_level"] == 1.5
    print("  PASS: State registered and inspectable.")
    
    # --- Test 2: Check Planning ---
    print("\n--- Test 2: Dynamic Check Planning ---")
    planned = engine.plan_checks(
        "Run the safety interceptor test with zoom tuning",
        ["ScreenObserver", "SafetyInterceptor"]
    )
    rule_ids = [r["id"] for r in planned]
    assert "R1_NO_REFUSAL" in rule_ids, "Core rules must always be included."
    assert "R3_SAFETY_CHECK" in rule_ids, "Safety check should be planned for safety-related tasks."
    assert "R5_AUTO_TUNE_SANITY" in rule_ids, "Auto-tune check should be planned when zoom is mentioned."
    print(f"  PASS: Planned {len(planned)} checks: {rule_ids}")
    
    # --- Test 3: Evaluation (all passing) ---
    print("\n--- Test 3: Evaluation (Healthy System) ---")
    all_passed, findings = engine.evaluate(planned, state)
    for f in findings:
        status = "PASS" if f["passed"] else "FAIL"
        print(f"  [{status}] {f['rule_id']}: {f['reason']}")
    assert all_passed, "All checks should pass on a healthy system."
    print("  PASS: All checks passed on healthy state.")
    
    # --- Test 4: Evaluation (unhealthy zoom) ---
    print("\n--- Test 4: Evaluation (Unhealthy: Zoom out of bounds) ---")
    sick_state = dict(state)
    sick_state["zoom_level"] = 5.0  # Out of bounds!
    planned_zoom = engine.plan_checks("Check auto tune zoom level", ["ConfigManager"])
    all_passed_sick, findings_sick = engine.evaluate(planned_zoom, sick_state)
    
    zoom_finding = next((f for f in findings_sick if f["rule_id"] == "R5_AUTO_TUNE_SANITY"), None)
    assert zoom_finding is not None, "Zoom check should have run."
    assert not zoom_finding["passed"], "Zoom 5.0x should FAIL the sanity check."
    print(f"  PASS: Correctly caught zoom 5.0x — {zoom_finding['reason']}")
    
    # --- Test 5: Evaluation (unauthorized action) ---
    print("\n--- Test 5: Evaluation (RBAC Violation) ---")
    rbac_state = dict(state)
    rbac_state["power_level"] = 0  # OBSERVER
    rbac_state["actions_attempted"] = ["click"]
    rbac_state["blocked_click"] = False  # Not blocked!
    planned_rbac = engine.plan_checks("Test power level executor observer", ["Interceptor"])
    all_passed_rbac, findings_rbac = engine.evaluate(planned_rbac, rbac_state)
    
    rbac_finding = next((f for f in findings_rbac if f["rule_id"] == "R7_POWER_LEVEL_AUDIT"), None)
    assert rbac_finding is not None, "RBAC check should have run."
    assert not rbac_finding["passed"], "Unblocked click at OBSERVER level should FAIL."
    print(f"  PASS: Correctly caught RBAC violation — {rbac_finding['reason']}")
    
    # --- Test 6: Diagnostic Report ---
    print("\n--- Test 6: Diagnostic Report ---")
    report = engine.get_diagnostic_report()
    print(report)
    assert "INTROSPECTION DIAGNOSTIC REPORT" in report
    assert "Rule Performance" in report
    print("  PASS: Diagnostic report generated.")
    
    print("\n" + "=" * 60)
    print("  ALL INTROSPECTION TESTS PASSED")
    print("=" * 60)
    return True


# =============================================================
# INLINE TEST: Swarm Architecture (with fixed imports)
# =============================================================
def test_swarm_fixed():
    """Test the Swarm's TaskTree and Scheduler with corrected import paths."""
    # Add the nanobot parent directory so `microgravity.agent` resolves
    nanobot_parent = nanobot_root.parent
    if str(nanobot_parent) not in sys.path:
        sys.path.insert(0, str(nanobot_parent))
    
    print("\n" + "=" * 60)
    print("  SWARM ARCHITECTURE TEST (Fixed Imports)")
    print("=" * 60)
    
    try:
        from microgravity.agent.task_tree import TaskTree
        from microgravity.agent.scheduler import Scheduler
        from microgravity.agent.memory import MemoryStore
        print("  PASS: All Swarm modules imported successfully.")
    except ImportError as e:
        print(f"  FAIL: Import error — {e}")
        print("  The nanobot modules may have additional dependencies.")
        return False
    
    import shutil
    workspace = project_root / "test_swarm_fixed"
    if workspace.exists():
        shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir()
    
    try:
        tree = TaskTree(workspace)
        print("  PASS: TaskTree initialized.")
        
        # Create a simple 3-task DAG
        t1 = tree.add_task("Design API schema", priority="high", labels=["api"])
        t2 = tree.add_task("Implement endpoints", depends_on=[t1.id], labels=["api"])
        t3 = tree.add_task("Write tests", depends_on=[t2.id], labels=["testing"])
        assert len(tree.get_all_tasks()) == 3
        print(f"  PASS: Created task DAG with 3 nodes: {t1.id}, {t2.id}, {t3.id}")
        
        # Verify dependency blocking
        err = tree.start_task(t2.id)
        assert err is not None
        print(f"  PASS: Dependency blocking works — {err}")
        
        # Progress t1 and verify t2 unblocks
        tree.start_task(t1.id)
        tree.complete_task(t1.id, consequence="REST API schema finalized")
        ready = tree.get_ready_tasks()
        assert any(t.id == t2.id for t in ready)
        print(f"  PASS: After t1 complete, t2 is ready.")
        
        # Template extraction
        template = tree.extract_template([t1.id, t2.id, t3.id])
        assert len(template["steps"]) == 3
        print(f"  PASS: Template extracted with {len(template['steps'])} steps.")
        
        print("\n  ALL SWARM TESTS PASSED")
        
    except Exception as e:
        print(f"  FAIL: {e}")
        return False
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
    
    print("=" * 60)
    return True


# =============================================================
# MAIN RUNNER
# =============================================================
TEST_SUITE = [
    # Architecture Phase Tests (subprocess)
    ("ARCH | Task Classification",   test_dir / "test_task_classification.py"),
    ("ARCH | UI Profile Database",   test_dir / "test_ui_profile.py"),
    ("ARCH | Safety Interceptor",    test_dir / "test_interceptor.py"),
    ("ARCH | Auto-Tuning Loop",      test_dir / "test_autotune.py"),
    ("SCEN | Scenario Modeling",     test_dir / "test_scenarios.py"),
    ("SCEN | Full Integration",      test_dir / "test_integration_master.py"),
]

def run_subprocess_test(name, script_path, timeout=60):
    if not script_path.exists():
        return False, 0.0
    print(f"\n{'='*60}")
    print(f"  RUNNING: {name}")
    print(f"{'='*60}")
    start = time.time()
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(project_root),
            capture_output=True, text=True, timeout=timeout
        )
        elapsed = time.time() - start
        lines = [l for l in (result.stdout + result.stderr).strip().split('\n') if l.strip()]
        for line in lines[-10:]:
            print(f"  | {line[:100]}")
        passed = result.returncode == 0
        print(f"\n  Result: [{'PASS' if passed else 'FAIL'}] in {elapsed:.1f}s")
        return passed, elapsed
    except subprocess.TimeoutExpired:
        return False, timeout
    except Exception as e:
        print(f"  ERROR: {e}")
        return False, 0.0

def main():
    print("=" * 60)
    print("  MICROGRAVITY AGENTIC OS")
    print("  UI Agent + Swarm + Introspection")
    print("  Complete System Validation")
    print("=" * 60)
    
    results = []
    total_start = time.time()
    
    # Run architecture + scenario subprocess tests
    for name, script in TEST_SUITE:
        passed, elapsed = run_subprocess_test(name, script)
        results.append((name, passed, elapsed))
    
    # Run inline introspection test
    print()
    start = time.time()
    try:
        intro_passed = test_introspection()
    except Exception as e:
        print(f"  INTROSPECTION ERROR: {e}")
        intro_passed = False
    results.append(("INSP | Introspection Engine", intro_passed, time.time() - start))
    
    # Run inline swarm test (with fixed imports)
    start = time.time()
    try:
        swarm_passed = test_swarm_fixed()
    except Exception as e:
        print(f"  SWARM ERROR: {e}")
        swarm_passed = False
    results.append(("SWRM | Swarm Architecture", swarm_passed, time.time() - start))
    
    # Run UI Agent test (subprocess)
    ui_agent_script = test_dir / "test_ui_agent.py"
    passed, elapsed = run_subprocess_test("UIAG | UI Agent Prototype", ui_agent_script)
    results.append(("UIAG | UI Agent Prototype", passed, elapsed))
    
    total_time = time.time() - total_start
    
    # FINAL REPORT
    print(f"\n\n{'='*60}")
    print("  FINAL REPORT")
    print(f"{'='*60}")
    
    current_layer = ""
    for name, passed, elapsed in results:
        layer = name.split("|")[0].strip()
        test_name = name.split("|")[1].strip()
        if layer != current_layer:
            current_layer = layer
            label = {"ARCH":"Architecture","SCEN":"Scenarios","INSP":"Introspection","SWRM":"Swarm","UIAG":"UI Agent"}.get(layer, layer)
            print(f"\n  --- {label} ---")
        icon = "[OK]" if passed else "[!!]"
        print(f"  {icon} {test_name:<35} {'PASS' if passed else 'FAIL':>6}  ({elapsed:.1f}s)")
    
    passed_count = sum(1 for _, p, _ in results if p)
    total_count = len(results)
    print(f"\n  TOTAL: {passed_count}/{total_count} passed in {total_time:.1f}s")
    print(f"{'='*60}")
    
    sys.exit(0 if passed_count == total_count else 1)

if __name__ == "__main__":
    main()
