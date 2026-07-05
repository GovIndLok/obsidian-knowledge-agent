import re
from pathlib import Path

class KnowledgeAnalyzer:
    def analyze(self, notes: list[dict]) -> dict:
        """
        Analyzes the collected notes to build understanding.
        Since this runs in Python, it performs static analysis.
        The LLM agent will use this output to reason further.
        """
        concepts = []
        scratch_work = []
        links = {}
        
        # Track base names to full paths
        base_names = {}
        duplicate_concepts = []
        
        for note in notes:
            path = note["path"]
            content = note["content"]
            
            # Simple heuristic for concepts vs scratch: presence of tags or length
            if "#scratch" in content or len(content) < 50:
                scratch_work.append(path)
            else:
                concepts.append(path)
                
            # Track duplicates
            base_name = Path(path).stem
            if base_name in base_names:
                duplicate_concepts.append(path)
                if base_names[base_name] not in duplicate_concepts:
                    duplicate_concepts.append(base_names[base_name])
            else:
                base_names[base_name] = path
                
            # Extract wikilinks [[Link]]
            found_links = re.findall(r'\[\[(.*?)\]\]', content)
            links[path] = [link.split('|')[0] for link in found_links]
            
        # Find unresolved references
        unresolved_references = []
        for note_path, note_links in links.items():
            for link in note_links:
                if link not in base_names:
                    unresolved_references.append(link)
                    
        return {
            "concepts": concepts,
            "scratch_work": scratch_work,
            "relationships": links,
            "total_notes": len(notes),
            "duplicate_concepts": duplicate_concepts,
            "unresolved_references": list(set(unresolved_references))
        }
