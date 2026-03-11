import asyncio
import sys
from pathlib import Path

# Add project root and src to path
project_root = Path(r"C:\Users\HP\Downloads\micro gravity - Copy")
sys.path.insert(0, str(project_root))

from src.kernel.interceptor import SafetyInterceptor, PowerLevel

def test_interceptor():
    print("Testing Safety Interceptor (RBAC)...\n")
    
    # 1. Test Observer (Lowest Power)
    print("--- Level 0: OBSERVER Test ---")
    safe_view_action = {"action": "parse", "target": "dom_tree"}
    unsafe_click_action = {"action": "click", "target": "buy_button"}
    
    is_safe, reason = SafetyInterceptor.evaluate_action(safe_view_action, PowerLevel.OBSERVER)
    assert is_safe == True, "Observer failed safe view action."
    
    is_safe, reason = SafetyInterceptor.evaluate_action(unsafe_click_action, PowerLevel.OBSERVER)
    assert is_safe == False, "Observer clicked! Security flaw."
    print("PASS: Observer restrictions working.")

    # 2. Test Operator
    print("\n--- Level 1: OPERATOR Test ---")
    operator_click = {"action": "click", "target": "next_page_btn"}
    operator_type = {"action": "type", "target": "email_input", "value": "test@test.com"}
    operator_danger = {"action": "type", "target": "password_input_field", "value": "123"}
    
    is_safe, reason = SafetyInterceptor.evaluate_action(operator_click, PowerLevel.OPERATOR)
    assert is_safe == True, "Operator failed safe click action."
    
    is_safe, reason = SafetyInterceptor.evaluate_action(operator_type, PowerLevel.OPERATOR)
    assert is_safe == False, "Operator allowed to type text!"
    
    is_safe, reason = SafetyInterceptor.evaluate_action(operator_danger, PowerLevel.OPERATOR)
    assert is_safe == False, "Operator accessed sensitive field!"
    print("PASS: Operator restrictions working.")

    # 3. Test Executor vs Universal Non-Negotiables
    print("\n--- Level 2: EXECUTOR Test ---")
    executor_submit = {"action": "submit", "target": "checkout_form"}
    malicious_terminal_1 = {"action": "run_terminal", "target": "bash", "value": "rm -rf /var/www"}
    malicious_terminal_2 = {"action": "run_terminal", "target": "bash", "value": ":(){ :|:& };:"} # Fork bomb
    
    is_safe, reason = SafetyInterceptor.evaluate_action(executor_submit, PowerLevel.EXECUTOR)
    assert is_safe == True, "Executor failed normal submit."
    
    is_safe, reason = SafetyInterceptor.evaluate_action(malicious_terminal_1, PowerLevel.EXECUTOR)
    assert is_safe == False, "Executor allowed rm -rf!"
    
    is_safe, reason = SafetyInterceptor.evaluate_action(malicious_terminal_2, PowerLevel.EXECUTOR)
    assert is_safe == False, "Executor allowed Fork Bomb!"
    
    print("PASS: Universal Non-Negotiables caught malicious intent from Executor.")
    print("\nAll Safety Interceptor Tests Passed Successfully!")

if __name__ == "__main__":
    test_interceptor()
