import json
from pathlib import Path
from ..base import BasePublisherTarget

class OKFPublisher(BasePublisherTarget):
    def generate(self, bundle: dict, output_dir: Path) -> None:
        """
        Generates the OKF directory structure and files.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # OKF requires an index.md
        index_path = output_dir / "index.md"
        title = bundle.get("title", "Knowledge Bundle")
        
        index_content = f"# {title}\n\n## Concepts\n"
        for concept in bundle.get("concepts", []):
            index_content += f"- [[{concept}]]\n"
            
        index_path.write_text(index_content, encoding="utf-8")
        
        # Write metadata.json
        meta_path = output_dir / "metadata.json"
        meta_path.write_text(json.dumps(bundle.get("metadata", {}), indent=2), encoding="utf-8")
        
        # Write notes
        notes_dir = output_dir / "notes"
        notes_dir.mkdir(exist_ok=True)
        
        for path, content in bundle.get("content", {}).items():
            # In OKF, it might just drop them all into notes/
            # and we should ensure no path traversal issues.
            safe_name = Path(path).name
            note_path = notes_dir / safe_name
            note_path.write_text(content, encoding="utf-8")
            
    def validate(self, output_dir: Path) -> dict:
        # Implementation typically in OKFValidator, keeping signature for BasePublisherTarget
        from .validator import OKFValidator
        return OKFValidator().validate(output_dir)
