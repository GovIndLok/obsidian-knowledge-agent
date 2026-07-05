import pytest
from pathlib import Path
from app.publisher.collector import NoteCollector

def test_note_collector_reads_content(tmp_path: Path):
    # Setup mock vault
    vault_path = tmp_path / "vault"
    vault_path.mkdir()
    
    note_path = vault_path / "note1.md"
    note_path.write_text("Hello World", encoding="utf-8")
    
    collector = NoteCollector(vault_path)
    result = collector.collect(["note1.md"])
    
    assert len(result) == 1
    assert result[0]["path"] == "note1.md"
    assert result[0]["content"] == "Hello World"

def test_note_collector_ignores_missing_files(tmp_path: Path):
    vault_path = tmp_path / "vault"
    vault_path.mkdir()
    
    collector = NoteCollector(vault_path)
    result = collector.collect(["missing.md"])
    
    assert len(result) == 0

def test_note_collector_prevents_traversal(tmp_path: Path):
    vault_path = tmp_path / "vault"
    vault_path.mkdir()
    
    secret_file = tmp_path / "secret.txt"
    secret_file.write_text("secret")
    
    collector = NoteCollector(vault_path)
    result = collector.collect(["../secret.txt"])
    
    assert len(result) == 0
