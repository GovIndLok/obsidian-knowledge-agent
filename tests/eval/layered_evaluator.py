def verify_tool_selection(trace: dict) -> tuple[bool, str]:
    """
    Verifies that the agent selected the publish_notes tool at least once.
    """
    tool_calls = trace.get("tool_calls", [])
    if not tool_calls:
        return False, "No tool calls were made."
        
    for call in tool_calls:
        if call.get("tool") == "publish_notes":
            return True, "Correct tool 'publish_notes' selected."
            
    return False, "'publish_notes' tool was never selected."

def verify_workflow_sequence(trace: dict) -> tuple[bool, str]:
    """
    Verifies the correct sequence: action="plan" must occur before action="execute".
    If action="execute" occurs without a prior "plan", it fails.
    """
    tool_calls = trace.get("tool_calls", [])
    has_planned = False
    
    for call in tool_calls:
        if call.get("tool") == "publish_notes":
            action = call.get("args", {}).get("action")
            if action == "plan":
                has_planned = True
            elif action == "execute":
                if not has_planned:
                    return False, "Executed without planning first."
    
    # If the workflow doesn't even plan, we might consider it failed if they were supposed to.
    # But some scenarios (like out of scope) might just refuse and make no calls.
    # We will just verify that if execute happens, plan happened first.
    return True, "Workflow sequence invariants held."

def verify_no_vault_modification(trace: dict) -> tuple[bool, str]:
    """
    Verifies that no tools modified the vault during a publish operation.
    """
    if trace.get("vault_modified", False):
        return False, "Vault was unexpectedly modified during publish."
    return True, "No vault modification detected."
