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
    assert (output_dir / "log.md").exists()
    assert (output_dir / "concept.md").exists()
    
    index_content = (output_dir / "index.md").read_text()
    assert "My OKF" in index_content
    # The output format for index.md uses: * [Title](relative-url) - desc
    assert "* [concept](concept.md)" in index_content
    
    concept_content = (output_dir / "concept.md").read_text()
    assert "type: Concept" in concept_content
    assert "title: concept" in concept_content

def test_okf_validator_valid_bundle(tmp_path: Path):
    output_dir = tmp_path / "okf_export"
    output_dir.mkdir()
    
    # Root index.md with frontmatter (allowed) and a heading
    (output_dir / "index.md").write_text("---\nokf_version: \"0.1\"\n---\n# My OKF\n")
    # log.md with date heading
    (output_dir / "log.md").write_text("# Bundle Update Log\n\n## 2026-07-06\n* **Creation**: Init\n")
    # Concept with YAML frontmatter containing 'type'
    (output_dir / "concept.md").write_text("---\ntype: Concept\ntitle: test\n---\nBody content\n")
    
    validator = OKFValidator()
    result = validator.validate(output_dir)
    
    assert result["valid"] is True
    assert len(result["errors"]) == 0

def test_okf_validator_invalid_bundle(tmp_path: Path):
    output_dir = tmp_path / "okf_export"
    output_dir.mkdir()
    
    # Root index.md missing heading
    (output_dir / "index.md").write_text("---\nokf_version: \"0.1\"\n---\n")
    # log.md missing date heading
    (output_dir / "log.md").write_text("# Log\n")
    # Concept missing type
    (output_dir / "concept.md").write_text("---\ntitle: test\n---\nBody\n")
    
    validator = OKFValidator()
    result = validator.validate(output_dir)
    
    assert result["valid"] is False
    # Errors should mention index.md, log.md, and concept.md validation issues
    assert any("must contain at least one section/group heading" in e for e in result["errors"])
    assert any("must contain at least one ISO 8601 date heading" in e for e in result["errors"])
    assert any("is missing required, non-empty 'type'" in e for e in result["errors"])
