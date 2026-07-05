from pathlib import Path
from .collector import NoteCollector
from .analyzer import KnowledgeAnalyzer
from .builder import KnowledgeModelBuilder
from .plan import PublishingPlan
from .targets.okf.generator import OKFPublisher
from .targets.okf.validator import OKFValidator

class PublishingSession:
    def __init__(self, vault_path: Path, selected_notes: list[str], metadata: dict | None = None):
        self.vault_path = vault_path
        self.selected_notes = selected_notes
        self.metadata = metadata or {}
        
    def plan(self) -> PublishingPlan:
        """
        Executes stages 1-3 to generate a plan for the agent.
        """
        collector = NoteCollector(self.vault_path)
        collected_notes = collector.collect(self.selected_notes)
        
        analyzer = KnowledgeAnalyzer()
        analysis = analyzer.analyze(collected_notes)
        
        return PublishingPlan(
            title=self.metadata.get("title", "Untitled Bundle"),
            notes_included=[note["path"] for note in collected_notes],
            concepts=analysis.get("concepts", []),
            scratch_work=analysis.get("scratch_work", []),
            relationships=analysis.get("relationships", {}),
            duplicate_concepts=analysis.get("duplicate_concepts", []),
            unresolved_references=analysis.get("unresolved_references", [])
        )
        
    def execute(self, output_dir: Path, target_format: str = "okf") -> dict:
        """
        Executes stages 4-6 after approval.
        """
        collector = NoteCollector(self.vault_path)
        collected_notes = collector.collect(self.selected_notes)
        
        analyzer = KnowledgeAnalyzer()
        analysis = analyzer.analyze(collected_notes)
        
        builder = KnowledgeModelBuilder()
        knowledge_bundle = builder.build(collected_notes, analysis, self.metadata)
        
        if target_format.lower() == "okf":
            publisher = OKFPublisher()
            publisher.generate(knowledge_bundle, output_dir)
            
            validator = OKFValidator()
            validation_result = validator.validate(output_dir)
            
            return {
                "status": "success" if validation_result["valid"] else "error",
                "validation": validation_result,
                "output_dir": str(output_dir)
            }
        else:
            return {"status": "error", "message": f"Unsupported target format: {target_format}"}
