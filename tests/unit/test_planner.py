from pathlib import Path
from unittest.mock import patch, MagicMock
from app.publisher.pipeline import PublishingSession
from app.publisher.plan import PublishingPlan

def test_publishing_planner_identifies_duplicates_and_unresolved():
    vault_path = Path("/mock/vault")
    selected_notes = ["Concept1.md", "folder/Concept1.md", "Concept2.md"]
    
    # Mocking NoteCollector to return predetermined notes
    collected_notes = [
        {"path": "Concept1.md", "content": "This links to [[MissingConcept]]."},
        {"path": "folder/Concept1.md", "content": "Another concept 1."},
        {"path": "Concept2.md", "content": "This links to [[Concept1]] and [[Concept3]]."}
    ]
    
    with patch("app.publisher.pipeline.NoteCollector") as MockCollector:
        instance = MockCollector.return_value
        instance.collect.return_value = collected_notes
        
        session = PublishingSession(vault_path, selected_notes)
        plan = session.plan()
        
        assert isinstance(plan, PublishingPlan)
        assert len(plan.duplicate_concepts) == 2
        assert "Concept1.md" in plan.duplicate_concepts
        assert "folder/Concept1.md" in plan.duplicate_concepts
        
        # MissingConcept and Concept3 are unresolved
        assert len(plan.unresolved_references) == 2
        assert "MissingConcept" in plan.unresolved_references
        assert "Concept3" in plan.unresolved_references
