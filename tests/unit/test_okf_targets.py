import pytest
from pathlib import Path
from app.publisher.targets.okf.generator import OKFPublisher
from app.publisher.targets.okf.validator import OKFValidator

def test_okf_publisher_creates_bundle(tmp_path: Path):
    bundle = {
        "title": "My OKF",
        "concepts": ["concept.md"],
        "metadata": {"author": "Test"},
        "content": {"concept.md": "Content"}
    }
    
    output_dir = tmp_path / "okf_export"
    publisher = OKFPublisher()
    publisher.generate(bundle, output_dir)
    
    assert (output_dir / "index.md").exists()
    assert (output_dir / "metadata.json").exists()
    assert (output_dir / "notes" / "concept.md").exists()
    
    index_content = (output_dir / "index.md").read_text()
    assert "My OKF" in index_content
    assert "[[concept.md]]" in index_content

def test_okf_validator_valid_bundle(tmp_path: Path):
    output_dir = tmp_path / "okf_export"
    output_dir.mkdir()
    (output_dir / "index.md").write_text("index")
    (output_dir / "metadata.json").write_text("{}")
    (output_dir / "notes").mkdir()
    
    validator = OKFValidator()
    result = validator.validate(output_dir)
    
    assert result["valid"] is True
    assert len(result["errors"]) == 0

def test_okf_validator_missing_files(tmp_path: Path):
    output_dir = tmp_path / "okf_export"
    output_dir.mkdir()
    # Missing index.md and metadata.json
    (output_dir / "notes").mkdir()
    
    validator = OKFValidator()
    result = validator.validate(output_dir)
    
    assert result["valid"] is False
    assert any("index.md" in e for e in result["errors"])
    assert any("metadata.json" in e for e in result["errors"])
