import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from app.publisher.pipeline import PublishingSession
from app.tools import publish_notes
from google.adk.tools import ToolContext

def test_publishing_pipeline_end_to_end(tmp_path: Path):
    vault_path = tmp_path / "vault"
    vault_path.mkdir()
    (vault_path / "note1.md").write_text("Hello [[note2]]")
    (vault_path / "note2.md").write_text("World")
    
    output_dir = tmp_path / "okf_export"
    
    session = PublishingSession(vault_path, ["note1.md", "note2.md"], {"title": "Integration Test"})
    
    # 1. Plan
    plan = session.plan()
    assert plan.title == "Integration Test"
    assert "note1.md" in plan.notes_included
    assert "note2.md" in plan.notes_included
    
    # 2. Execute
    result = session.execute(output_dir, "okf")
    assert result["status"] == "success"
    assert result["validation"]["valid"] is True
    
    # Verify outputs
    assert (output_dir / "index.md").exists()
    assert (output_dir / "note1.md").exists()

def test_publishing_pipeline_validation_failure(tmp_path: Path):
    vault_path = tmp_path / "vault"
    vault_path.mkdir()
    (vault_path / "note1.md").write_text("Hello")
    
    output_dir = tmp_path / "okf_export"
    
    session = PublishingSession(vault_path, ["note1.md"])
    
    # Mock validator to fail
    with patch("app.publisher.pipeline.OKFValidator") as MockValidator:
        instance = MockValidator.return_value
        instance.validate.return_value = {"valid": False, "errors": ["Mock failure"]}
        
        result = session.execute(output_dir, "okf")
        
        assert result["status"] == "error"
        assert result["validation"]["valid"] is False
        assert "Mock failure" in result["validation"]["errors"]

def test_publish_notes_tool(tmp_path: Path):
    vault_path = tmp_path / "vault"
    vault_path.mkdir()
    (vault_path / "note1.md").write_text("Hello")
    
    tool_context = MagicMock(spec=ToolContext)
    tool_context.state = {"vault_path": str(vault_path)}
    
    # Test plan action
    with patch("app.tools._get_vault_path", return_value=vault_path):
        result_plan = publish_notes(
            action="plan", 
            selected_notes=["note1.md"], 
            metadata={"title": "Tool Test"},
            tool_context=tool_context
        )
        assert result_plan["status"] == "success"
        assert result_plan["plan"]["title"] == "Tool Test"
        
        # Test execute action
        with patch("app.publisher.pipeline.PublishingSession") as MockSession:
            session_instance = MockSession.return_value
            session_instance.execute.return_value = {"status": "success", "validation": {"valid": True}, "output_dir": "/mock/out"}
            
            result_execute = publish_notes(
                action="execute", 
                selected_notes=["note1.md"], 
                tool_context=tool_context
            )
            assert result_execute["status"] == "success"
