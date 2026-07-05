from app.publisher.builder import KnowledgeModelBuilder

def test_knowledge_model_builder():
    builder = KnowledgeModelBuilder()
    
    notes = [
        {"path": "note1.md", "content": "hello"}
    ]
    analysis = {
        "concepts": ["note1.md"],
        "relationships": {},
    }
    metadata = {"title": "Test Title"}
    
    bundle = builder.build(notes, analysis, metadata)
    
    assert bundle["title"] == "Test Title"
    assert bundle["metadata"] == metadata
    assert bundle["concepts"] == ["note1.md"]
    assert bundle["content"]["note1.md"] == "hello"
