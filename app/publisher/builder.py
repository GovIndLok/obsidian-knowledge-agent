class KnowledgeModelBuilder:
    def build(self, notes: list[dict], analysis: dict, metadata: dict) -> dict:
        """
        Constructs the internal KnowledgeBundle representation.
        """
        bundle = {
            "title": metadata.get("title", "Untitled Bundle"),
            "metadata": metadata,
            "concepts": analysis.get("concepts", []),
            "relationships": analysis.get("relationships", {}),
            "content": {}
        }
        
        for note in notes:
            bundle["content"][note["path"]] = note["content"]
            
        return bundle
