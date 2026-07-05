from pathlib import Path

class OKFValidator:
    def validate(self, output_dir: Path) -> dict:
        """
        Validates the generated OKF bundle.
        """
        errors = []
        
        if not output_dir.exists():
            errors.append(f"Output directory does not exist: {output_dir}")
            return {"valid": False, "errors": errors}
            
        if not (output_dir / "index.md").exists():
            errors.append("Missing required file: index.md")
            
        if not (output_dir / "metadata.json").exists():
            errors.append("Missing required file: metadata.json")
            
        if not (output_dir / "notes").exists() or not (output_dir / "notes").is_dir():
            errors.append("Missing required directory: notes/")
            
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
