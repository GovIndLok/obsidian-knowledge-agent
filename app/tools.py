# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import shutil
from pathlib import Path

from google.adk.tools import ToolContext


def _get_vault_path(tool_context: ToolContext = None) -> Path:
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
    try:
        if vault_path.exists():
            # Path already exists — just validate it is a directory.
            if not vault_path.is_dir():
                raise ValueError("Path exists but is not a directory.")
        else:
            # Path doesn't exist — attempt to create it (may fail on read-only mounts).
            vault_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise ValueError(
            f"Vault path '{path_str}' is invalid. Current valid vault path: '{default_path_str}'. Details: {e!s}"
        )
    return vault_path


def _safe_resolve(relative_path: str, tool_context: ToolContext = None) -> Path:
    """Helper to safely resolve a path within the vault, preventing directory traversal."""
    vault_path = _get_vault_path(tool_context)
    resolved_path = (vault_path / relative_path).resolve()
    if not resolved_path.is_relative_to(vault_path):
        raise ValueError(
            f"Path traversal detected: {relative_path} is outside of vault {vault_path}"
        )
    return resolved_path


def set_vault_path(new_path: str, tool_context: ToolContext = None) -> dict:
    """Sets the active Obsidian vault directory path for the current session.

    Use this tool when the user requests to point to a new vault or change the active vault path.
    The directory must already exist on disk (e.g. a mounted Obsidian vault). If it does not
    exist, the tool will attempt to create it — but this may fail on read-only or restricted mounts.

    Args:
        new_path: The absolute directory path of the new Obsidian vault.

    Returns:
        A dict with 'status' indicating success or failure, and 'message' with details.
    """
    try:
        current_path = str(_get_vault_path(tool_context))
    except Exception:
        current_path = os.environ.get(
            "OBSIDIAN_VAULT_PATH", "/home/gov03/project/obsidian-organizer/vault"
        )

    try:
        path = Path(new_path).resolve()

        if path.exists():
            # Path already exists on disk — validate it is a directory.
            if not path.is_dir():
                return {
                    "status": "error",
                    "message": (
                        f"'{new_path}' exists but is a file, not a directory. "
                        f"Current vault path: '{current_path}'."
                    ),
                }
        else:
            # Path doesn't exist — try to create it.
            # This will fail on read-only or restricted mounts.
            try:
                path.mkdir(parents=True, exist_ok=True)
            except PermissionError:
                return {
                    "status": "error",
                    "message": (
                        f"Cannot access '{new_path}': directory does not exist and "
                        f"permission was denied when trying to create it. "
                        f"Make sure the path already exists and is accessible. "
                        f"Current vault path: '{current_path}'."
                    ),
                }
            except OSError as e:
                return {
                    "status": "error",
                    "message": (
                        f"Cannot create '{new_path}': {e.strerror}. "
                        f"Current vault path: '{current_path}'."
                    ),
                }

        if tool_context:
            tool_context.state["vault_path"] = str(path)
        return {
            "status": "success",
            "message": f"Vault path successfully changed to '{path!s}'.",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": (
                f"Unexpected error setting vault path to '{new_path}': {e!s}. "
                f"Current vault path: '{current_path}'."
            ),
        }


def list_vault_notes(tool_context: ToolContext = None) -> dict:
    """Lists all markdown files (.md) in the Obsidian vault recursively.

    Skips known Obsidian config/system folders (.obsidian, .trash, .git).
    Returns the path that was actually scanned so errors can be diagnosed.

    Returns:
        A dict with:
          - 'status': 'success' or 'error'
          - 'vault_path': the absolute path that was scanned
          - 'notes': list of relative .md file paths
          - 'total_files': total number of files found (all extensions) — useful
            for diagnosing "vault exists but has no .md files" vs "wrong path"
    """
    # Obsidian system folders to skip entirely
    SKIP_DIRS = {".obsidian", ".trash", ".git", ".adk"}

    try:
        vault_path = _get_vault_path(tool_context)
        notes = []
        total_files = 0
        for root, dirs, files in os.walk(vault_path):
            # Prune known Obsidian/system hidden directories in-place
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

            for file in files:
                total_files += 1
                if file.endswith(".md"):
                    full_path = Path(root) / file
                    rel_path = full_path.relative_to(vault_path)
                    notes.append(str(rel_path))

        return {
            "status": "success",
            "vault_path": str(vault_path),
            "notes": notes,
            "total_files": total_files,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}



def read_note(note_path: str, tool_context: ToolContext = None) -> dict:
    """Reads the text content of a specific note file inside the vault.

    Args:
        note_path: The relative path of the note file (e.g., 'topic/Note.md').

    Returns:
        A dict with 'status', 'note_path', and 'content' of the note.
    """
    try:
        target_path = _safe_resolve(note_path, tool_context)
        if not target_path.exists():
            return {"status": "error", "message": f"Note not found: {note_path}"}
        if not target_path.is_file():
            return {"status": "error", "message": f"Path is not a file: {note_path}"}

        content = target_path.read_text(encoding="utf-8")
        return {"status": "success", "note_path": note_path, "content": content}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def write_note(note_path: str, content: str, tool_context: ToolContext = None) -> dict:
    """Creates a new note or overwrites/updates an existing note with new content.

    Args:
        note_path: The relative path of the note file to write (e.g., 'topic/Note.md').
        content: The complete markdown content to write to the file.

    Returns:
        A dict with 'status' indicating success or failure.
    """
    try:
        target_path = _safe_resolve(note_path, tool_context)
        # Ensure parent directories exist
        target_path.parent.mkdir(parents=True, exist_ok=True)

        target_path.write_text(content, encoding="utf-8")
        return {"status": "success", "note_path": note_path}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def create_vault_directory(folder_name: str, tool_context: ToolContext = None) -> dict:
    """Creates a new subdirectory inside the vault to establish hierarchical folders.

    Args:
        folder_name: The relative path of the folder to create (e.g., 'Personal Finance').

    Returns:
        A dict with 'status' indicating success or failure.
    """
    try:
        target_path = _safe_resolve(folder_name, tool_context)
        target_path.mkdir(parents=True, exist_ok=True)
        return {"status": "success", "folder_name": folder_name}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def move_note(
    note_path: str, destination_folder: str, tool_context: ToolContext = None
) -> dict:
    """Moves a note to a different folder inside the vault.

    Args:
        note_path: The relative path of the note file to move (e.g., 'Note.md').
        destination_folder: The relative path of the target folder (e.g., 'Archive').

    Returns:
        A dict with 'status' indicating success or failure.
    """
    try:
        source_path = _safe_resolve(note_path, tool_context)
        dest_folder_path = _safe_resolve(destination_folder, tool_context)

        if not source_path.exists():
            return {"status": "error", "message": f"Source note not found: {note_path}"}

        # Create destination folder if it doesn't exist
        dest_folder_path.mkdir(parents=True, exist_ok=True)
        dest_file_path = dest_folder_path / source_path.name

        shutil.move(str(source_path), str(dest_file_path))
        return {
            "status": "success",
            "source": note_path,
            "destination": str(
                dest_file_path.relative_to(_get_vault_path(tool_context))
            ),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
