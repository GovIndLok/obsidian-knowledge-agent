import os
from pathlib import Path
from google.adk.tools import ToolContext

def get_vault_path(tool_context: ToolContext | None = None) -> Path:
    """Helper to get the configured vault path from session state or environment variables."""
    default_path_str = os.environ.get(
        "OBSIDIAN_VAULT_PATH", "/home/gov03/project/obsidian-organizer/vault"
    )

    path_str = None
    if tool_context and "vault_path" in tool_context.state:
        path_str = tool_context.state["vault_path"]

    if not path_str:
        path_str = default_path_str

    vault_path = Path(path_str).resolve()
    if not vault_path.exists():
        raise ValueError(f"Vault path '{vault_path}' does not exist.")
    if not vault_path.is_dir():
        raise ValueError(f"Vault path '{vault_path}' exists but is not a directory.")
    
    return vault_path

def safe_resolve(relative_path: str, tool_context: ToolContext | None = None) -> Path:
    """Helper to safely resolve a path within the vault, preventing directory traversal."""
    vault_path = get_vault_path(tool_context)
    resolved_path = (vault_path / relative_path).resolve()
    if not resolved_path.is_relative_to(vault_path):
        raise ValueError(
            f"Path traversal detected: {relative_path} is outside of vault {vault_path}"
        )
    return resolved_path
