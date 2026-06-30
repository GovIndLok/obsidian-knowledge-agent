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
import hashlib
import json
import sqlite3
import datetime
import uuid
from pathlib import Path

from google.adk.tools import ToolContext


def _get_vault_path(tool_context: ToolContext | None = None) -> Path:
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


def _safe_resolve(relative_path: str, tool_context: ToolContext | None = None) -> Path:
    """Helper to safely resolve a path within the vault, preventing directory traversal."""
    vault_path = _get_vault_path(tool_context)
    resolved_path = (vault_path / relative_path).resolve()
    if not resolved_path.is_relative_to(vault_path):
        raise ValueError(
            f"Path traversal detected: {relative_path} is outside of vault {vault_path}"
        )
    return resolved_path


def set_vault_path(new_path: str, tool_context: ToolContext | None = None) -> dict:
    """Sets the active Obsidian vault directory path for the current session.

    Use this tool when the user requests to point to a new vault or change the active vault path.
    The directory must already exist on disk (e.g. a mounted Obsidian vault). If it does not
    exist, the tool will return an error informing the user.

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

        if not path.exists():
            return {
                "status": "error",
                "message": (
                    f"The specified vault path '{new_path}' does not exist. "
                    f"Please ensure the directory is created before pointing the agent to it. "
                    f"Current vault path: '{current_path}'."
                ),
            }

        # Path exists — validate it is a directory.
        if not path.is_dir():
            return {
                "status": "error",
                "message": (
                    f"'{new_path}' exists but is a file, not a directory. "
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


def list_vault_notes(tool_context: ToolContext | None = None) -> dict:
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



def read_note(note_path: str, tool_context: ToolContext | None = None) -> dict:
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


def update_note(note_path: str, find_text: str, replace_text: str, tool_context: ToolContext | None = None) -> dict:
    """Updates an existing note by finding and replacing specific text.
    Useful for modifying frontmatter or inserting wikilinks without rewriting the entire file.

    Args:
        note_path: The relative path of the note file (e.g., 'topic/Note.md').
        find_text: The exact text to find in the note.
        replace_text: The new text to replace it with.

    Returns:
        A dict with 'status' indicating success or failure.
    """
    try:
        target_path = _safe_resolve(note_path, tool_context)
        if not target_path.exists():
            return {"status": "error", "message": f"Note not found: {note_path}"}
        
        content = target_path.read_text(encoding="utf-8")
        if find_text not in content:
            return {"status": "error", "message": "The specified find_text was not found in the note."}
            
        new_content = content.replace(find_text, replace_text, 1)
        target_path.write_text(new_content, encoding="utf-8")
        return {"status": "success", "note_path": note_path}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def create_vault_directory(folder_name: str, tool_context: ToolContext | None = None) -> dict:
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
    note_path: str, destination_folder: str, tool_context: ToolContext | None = None
) -> dict:
    """Moves a note to a different folder inside the vault and updates wikilinks.

    Args:
        note_path: The relative path of the note file to move (e.g., 'Note.md').
        destination_folder: The relative path of the target folder (e.g., 'Archive').

    Returns:
        A dict with 'status' indicating success or failure.
    """
    try:
        vault_path = _get_vault_path(tool_context)
        source_path = _safe_resolve(note_path, tool_context)
        dest_folder_path = _safe_resolve(destination_folder, tool_context)

        if not source_path.exists():
            return {"status": "error", "message": f"Source note not found: {note_path}"}

        dest_file_path = dest_folder_path / source_path.name

        # Prevent silent overwrite on filename collision
        if dest_file_path.exists():
            return {"status": "error", "message": f"Destination file already exists: {dest_file_path.relative_to(vault_path)}"}

        # Create destination folder if it doesn't exist
        dest_folder_path.mkdir(parents=True, exist_ok=True)

        shutil.move(str(source_path), str(dest_file_path))
        
        # Update wikilinks
        old_rel_path = str(source_path.relative_to(vault_path))
        new_rel_path = str(dest_file_path.relative_to(vault_path))
        
        old_full = Path(old_rel_path).with_suffix("").as_posix()
        new_full = Path(new_rel_path).with_suffix("").as_posix()
        
        for root, dirs, files in os.walk(vault_path):
            if ".obsidian" in dirs: dirs.remove(".obsidian")
            if ".git" in dirs: dirs.remove(".git")
            for file in files:
                if file.endswith(".md"):
                    fpath = Path(root) / file
                    content = fpath.read_text(encoding="utf-8")
                    updated_content = content.replace(f"[[{old_full}]]", f"[[{new_full}]]")
                    updated_content = updated_content.replace(f"[[{old_full}|", f"[[{new_full}|")
                    if content != updated_content:
                        fpath.write_text(updated_content, encoding="utf-8")

        return {
            "status": "success",
            "source": note_path,
            "destination": new_rel_path,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _get_agent_dir():
    return Path(__file__).resolve().parent.parent / "obsidian-agent"


def _init_agent_dirs():
    agent_dir = _get_agent_dir()
    config_dir = agent_dir / "config"
    state_dir = agent_dir / "state"
    config_dir.mkdir(parents=True, exist_ok=True)
    state_dir.mkdir(parents=True, exist_ok=True)
    
    config_toml = config_dir / "config.toml"
    if not config_toml.exists():
        config_toml.write_text("")
        
    vaults_json = config_dir / "vaults.json"
    if not vaults_json.exists():
        vaults_json.write_text("{}")
        
    return config_dir, state_dir


def _get_vault_db_id(vault_path: Path) -> str:
    config_dir, _ = _init_agent_dirs()
    vaults_json = config_dir / "vaults.json"
    vaults = json.loads(vaults_json.read_text(encoding="utf-8"))
    
    vault_key = str(vault_path.resolve())
    now_iso = datetime.datetime.now().isoformat()
    
    if vault_key not in vaults:
        new_id = uuid.uuid4().hex[:8]
        vaults[vault_key] = {
            "id": new_id,
            "last_opened": now_iso
        }
    else:
        vaults[vault_key]["last_opened"] = now_iso
        
    vaults_json.write_text(json.dumps(vaults, indent=2), encoding="utf-8")
    return vaults[vault_key]["id"]


def _get_state_db_path(tool_context: ToolContext | None = None) -> Path:
    vault_path = _get_vault_path(tool_context)
    db_id = _get_vault_db_id(vault_path)
    _, state_dir = _init_agent_dirs()
    return state_dir / f"{db_id}.sqlite"


def _init_sqlite_db(db_path: Path):
    with sqlite3.connect(db_path) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS note_state (
                path TEXT PRIMARY KEY,
                hash TEXT NOT NULL,
                last_processed TEXT NOT NULL
            )
        ''')


def _load_state(db_path: Path) -> dict:
    _init_sqlite_db(db_path)
    state = {}
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute('SELECT path, hash FROM note_state')
        for row in cursor:
            state[row[0]] = row[1]
    return state


def _save_note_state(db_path: Path, path: str, hash_val: str):
    _init_sqlite_db(db_path)
    now_iso = datetime.datetime.now().isoformat()
    with sqlite3.connect(db_path) as conn:
        conn.execute('''
            INSERT INTO note_state (path, hash, last_processed)
            VALUES (?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                hash=excluded.hash,
                last_processed=excluded.last_processed
        ''', (path, hash_val, now_iso))


def _delete_note_state(db_path: Path, path: str):
    _init_sqlite_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute('DELETE FROM note_state WHERE path = ?', (path,))


def _compute_hash(file_path: Path) -> str:
    hasher = hashlib.sha256()
    hasher.update(file_path.read_bytes())
    return hasher.hexdigest()


def check_vault_changes(tool_context: ToolContext | None = None) -> dict:
    """Checks the entire vault for any changes by computing hashes and comparing with the saved database.
    
    Returns lists of 'changed', 'new', and 'deleted' notes. New notes are automatically added to the tracking database.
    
    Returns:
        dict with lists of changed, new, and deleted note paths.
    """
    try:
        vault_path = _get_vault_path(tool_context)
        db_path = _get_state_db_path(tool_context)
        state = _load_state(db_path)
        
        SKIP_DIRS = {".obsidian", ".trash", ".git", ".adk"}
        
        current_notes = {}
        for root, dirs, files in os.walk(vault_path):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for file in files:
                if file.endswith(".md"):
                    full_path = Path(root) / file
                    rel_path = str(full_path.relative_to(vault_path))
                    current_notes[rel_path] = full_path
                    
        changed = []
        new = []
        deleted = []
        
        for rel_path, full_path in current_notes.items():
            current_hash = _compute_hash(full_path)
            if rel_path not in state:
                _save_note_state(db_path, rel_path, current_hash)
                new.append(rel_path)
            elif state[rel_path] != current_hash:
                changed.append(rel_path)
                
        for rel_path in list(state.keys()):
            if rel_path not in current_notes:
                deleted.append(rel_path)
                
        return {
            "status": "success",
            "changed": changed,
            "new": new,
            "deleted": deleted
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def check_note_status(note_path: str, tool_context: ToolContext | None = None) -> dict:
    """Checks the status of a specific note by computing its hash and comparing it with the saved state.
    
    If the note is new (not in database), it will be added to the database automatically.
    If the note has changed, it will return the status 'changed' so you can look at the changes.
    If the note is deleted, it will return 'deleted'.
    
    Args:
        note_path: The relative path of the note file.
        
    Returns:
        dict containing 'status', 'note_path', and 'state' ('unchanged', 'changed', 'new', 'deleted').
    """
    try:
        db_path = _get_state_db_path(tool_context)
        state = _load_state(db_path)
        
        target_path = _safe_resolve(note_path, tool_context)
        
        if not target_path.exists():
            if note_path in state:
                return {"status": "success", "note_path": note_path, "state": "deleted"}
            else:
                return {"status": "error", "message": "Note does not exist and is not tracked."}
                
        current_hash = _compute_hash(target_path)
        
        if note_path not in state:
            _save_note_state(db_path, note_path, current_hash)
            return {"status": "success", "note_path": note_path, "state": "new"}
            
        saved_hash = state[note_path]
        
        if current_hash == saved_hash:
            return {"status": "success", "note_path": note_path, "state": "unchanged"}
        else:
            return {"status": "success", "note_path": note_path, "state": "changed"}
            
    except Exception as e:
        return {"status": "error", "message": str(e)}


def update_note_hash(note_path: str, tool_context: ToolContext | None = None) -> dict:
    """Updates the hash of a note in the state database after a change is made.
    If the note has been deleted, its entry in the state database is also deleted.
    
    Run this tool after every change made to a note.
    
    Args:
        note_path: The relative path of the note file.
        
    Returns:
        dict indicating success or failure.
    """
    try:
        db_path = _get_state_db_path(tool_context)
        state = _load_state(db_path)
        
        target_path = _safe_resolve(note_path, tool_context)
        
        if not target_path.exists():
            if note_path in state:
                _delete_note_state(db_path, note_path)
            return {"status": "success", "message": f"Note '{note_path}' deleted from tracking."}
            
        current_hash = _compute_hash(target_path)
        _save_note_state(db_path, note_path, current_hash)
        
        return {"status": "success", "message": f"Hash updated for '{note_path}'."}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}
