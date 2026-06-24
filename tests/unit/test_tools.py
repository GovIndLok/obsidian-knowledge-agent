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
from pathlib import Path
import pytest

from app.tools import list_vault_notes, read_note, write_note, create_vault_directory, move_note


@pytest.fixture(autouse=True)
def temp_vault(tmp_path, monkeypatch):
    """Sets up a clean, isolated temporary Obsidian vault for each test."""
    # Write mock files
    (tmp_path / "Agent Architectures.md").write_text(
        "# Agent Architectures\nThis note discusses the design of single-agent systems.",
        encoding="utf-8"
    )
    (tmp_path / "Active Coding Assistant.md").write_text(
        "# Active Coding Assistant\nAI coding assistants use advanced planning.",
        encoding="utf-8"
    )
    (tmp_path / "Chocolate Chip Cookies.md").write_text(
        "# Chocolate Chip Cookies\nIngredients:\n- Flour\n- Chocolate chips",
        encoding="utf-8"
    )
    # Monkeypatch the environment variable to point to our temp vault
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path))
    return tmp_path


def test_list_vault_notes():
    result = list_vault_notes()
    assert result["status"] == "success"
    assert "notes" in result
    assert len(result["notes"]) == 3
    assert "Agent Architectures.md" in result["notes"]
    assert "Chocolate Chip Cookies.md" in result["notes"]


def test_read_note():
    result = read_note("Chocolate Chip Cookies.md")
    assert result["status"] == "success"
    assert "content" in result
    assert "Flour" in result["content"]


def test_write_note():
    write_result = write_note("New Note.md", "# New Content")
    assert write_result["status"] == "success"

    read_result = read_note("New Note.md")
    assert read_result["status"] == "success"
    assert read_result["content"] == "# New Content"


def test_create_vault_directory():
    result = create_vault_directory("New Directory")
    assert result["status"] == "success"
    # Verify directory exists
    vault_path = Path(os.environ["OBSIDIAN_VAULT_PATH"])
    assert (vault_path / "New Directory").is_dir()


def test_move_note():
    result = move_note("Chocolate Chip Cookies.md", "Cooking")
    assert result["status"] == "success"
    
    # Verify file is moved
    vault_path = Path(os.environ["OBSIDIAN_VAULT_PATH"])
    assert not (vault_path / "Chocolate Chip Cookies.md").exists()
    assert (vault_path / "Cooking/Chocolate Chip Cookies.md").is_file()
