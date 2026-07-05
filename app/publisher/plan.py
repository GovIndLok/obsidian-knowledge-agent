from dataclasses import dataclass, field

@dataclass
class PublishingPlan:
    title: str
    notes_included: list[str] = field(default_factory=list)
    concepts: list[str] = field(default_factory=list)
    scratch_work: list[str] = field(default_factory=list)
    relationships: dict[str, list[str]] = field(default_factory=dict)
    duplicate_concepts: list[str] = field(default_factory=list)
    unresolved_references: list[str] = field(default_factory=list)
    message: str = "Plan generated successfully. Present this to the user for approval."
