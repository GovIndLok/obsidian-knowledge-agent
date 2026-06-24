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


def _get_vault_path() -> Path:
    """Helper to get the configured vault path from environment variables."""
    path_str = os.environ.get(
        "OBSIDIAN_VAULT_PATH", "/home/gov03/project/obsidian-organizer/vault"
    )
    vault_path = Path(path_str).resolve()
    # Ensure the vault directory exists
    vault_path.mkdir(parents=True, exist_ok=True)
    return vault_path


def _safe_resolve(relative_path: str) -> Path:
    """Helper to safely resolve a path within the vault, preventing directory traversal."""
    vault_path = _get_vault_path()
    resolved_path = (vault_path / relative_path).resolve()
    if not resolved_path.is_relative_to(vault_path):
        raise ValueError(
            f"Path traversal detected: {relative_path} is outside of vault {vault_path}"
        )
    return resolved_path


def list_vault_notes() -> dict:
    """Lists all markdown files (.md) in the Obsidian vault recursively.

    It ignores hidden configuration folders (e.g. starting with .obsidian or .git).

    Returns:
        A dict with 'status' (success/error) and a list of 'notes' containing relative paths.
    """
    try:
        vault_path = _get_vault_path()
        notes = []
        for root, dirs, files in os.walk(vault_path):
            # Prune hidden directories in-place (like .obsidian, .git)
            dirs[:] = [d for d in dirs if not d.startswith(".")]

            for file in files:
                if file.endswith(".md"):
                    full_path = Path(root) / file
                    rel_path = full_path.relative_to(vault_path)
                    notes.append(str(rel_path))

        return {"status": "success", "notes": notes}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def read_note(note_path: str) -> dict:
    """Reads the text content of a specific note file inside the vault.

    Args:
        note_path: The relative path of the note file (e.g., 'topic/Note.md').

    Returns:
        A dict with 'status', 'note_path', and 'content' of the note.
    """
    try:
        target_path = _safe_resolve(note_path)
        if not target_path.exists():
            return {"status": "error", "message": f"Note not found: {note_path}"}
        if not target_path.is_file():
            return {"status": "error", "message": f"Path is not a file: {note_path}"}

        content = target_path.read_text(encoding="utf-8")
        return {"status": "success", "note_path": note_path, "content": content}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def write_note(note_path: str, content: str) -> dict:
    """Creates a new note or overwrites/updates an existing note with new content.

    Args:
        note_path: The relative path of the note file to write (e.g., 'topic/Note.md').
        content: The complete markdown content to write to the file.

    Returns:
        A dict with 'status' indicating success or failure.
    """
    try:
        target_path = _safe_resolve(note_path)
        # Ensure parent directories exist
        target_path.parent.mkdir(parents=True, exist_ok=True)

        target_path.write_text(content, encoding="utf-8")
        return {"status": "success", "note_path": note_path}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def create_vault_directory(folder_name: str) -> dict:
    """Creates a new subdirectory inside the vault to establish hierarchical folders.

    Args:
        folder_name: The relative path of the folder to create (e.g., 'Personal Finance').

    Returns:
        A dict with 'status' indicating success or failure.
    """
    try:
        target_path = _safe_resolve(folder_name)
        target_path.mkdir(parents=True, exist_ok=True)
        return {"status": "success", "folder_name": folder_name}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def move_note(note_path: str, destination_folder: str) -> dict:
    """Moves a note to a different folder inside the vault.

    Args:
        note_path: The relative path of the note file to move (e.g., 'Note.md').
        destination_folder: The relative path of the target folder (e.g., 'Archive').

    Returns:
        A dict with 'status' indicating success or failure.
    """
    try:
        source_path = _safe_resolve(note_path)
        dest_folder_path = _safe_resolve(destination_folder)

        if not source_path.exists():
            return {"status": "error", "message": f"Source note not found: {note_path}"}

        # Create destination folder if it doesn't exist
        dest_folder_path.mkdir(parents=True, exist_ok=True)
        dest_file_path = dest_folder_path / source_path.name

        shutil.move(str(source_path), str(dest_file_path))
        return {
            "status": "success",
            "source": note_path,
            "destination": str(dest_file_path.relative_to(_get_vault_path())),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
