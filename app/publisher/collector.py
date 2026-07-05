from pathlib import Path

class NoteCollector:
    def __init__(self, vault_path: Path):
        self.vault_path = vault_path
        
    def collect(self, selected_notes: list[str]) -> list[dict]:
        collected = []
        for note_path in selected_notes:
            full_path = (self.vault_path / note_path).resolve()
            if not full_path.is_relative_to(self.vault_path):
                continue
            if full_path.exists() and full_path.is_file():
                content = full_path.read_text(encoding="utf-8")
                collected.append({
                    "path": note_path,
                    "content": content
                })
        return collected
