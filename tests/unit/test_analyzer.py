from app.publisher.analyzer import KnowledgeAnalyzer

def test_knowledge_analyzer_identifies_concepts_and_scratch():
    analyzer = KnowledgeAnalyzer()
    notes = [
        {"path": "concept.md", "content": "This is a very long concept note that exceeds fifty characters by a wide margin so it is definitely a concept."},
        {"path": "scratch.md", "content": "#scratch this is scratch work."},
        {"path": "short.md", "content": "Too short."}
    ]
    
    result = analyzer.analyze(notes)
    
    assert "concept.md" in result["concepts"]
    assert "scratch.md" in result["scratch_work"]
    assert "short.md" in result["scratch_work"]
    assert result["total_notes"] == 3

def test_knowledge_analyzer_parses_wikilinks():
    analyzer = KnowledgeAnalyzer()
    notes = [
        {"path": "A.md", "content": "Links to [[B]] and [[C|Alias]]."},
        {"path": "B.md", "content": "No links."},
        {"path": "C.md", "content": "Links back to [[A]]."}
    ]
    
    result = analyzer.analyze(notes)
    links = result["relationships"]
    
    assert "B" in links["A.md"]
    assert "C" in links["A.md"]  # Assuming the alias is stripped correctly
    assert len(links["B.md"]) == 0
    assert "A" in links["C.md"]
