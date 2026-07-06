import os
import yaml
import re
from pathlib import Path

class OKFValidator:
    def validate(self, output_dir: Path) -> dict:
        """
        Validates the generated OKF bundle according to the OKF v0.1 specification.
        """
        errors = []
        
        if not output_dir.exists():
            errors.append(f"Output directory does not exist: {output_dir}")
            return {"valid": False, "errors": errors}
            
        # Walk all files in output_dir
        for root, dirs, files in os.walk(output_dir):
            root_path = Path(root)
            # Skip hidden directories like .git
            if any(part.startswith('.') for part in root_path.relative_to(output_dir).parts):
                continue
                
            for filename in files:
                if not filename.endswith('.md'):
                    continue
                    
                file_path = root_path / filename
                rel_file_path = file_path.relative_to(output_dir)
                
                try:
                    content = file_path.read_text(encoding="utf-8")
                except Exception as e:
                    errors.append(f"Failed to read file '{rel_file_path}': {e}")
                    continue
                
                if filename == "index.md":
                    # Validate index.md structure:
                    # - Must contain no frontmatter, UNLESS it's the root index.md, which may declare okf_version: "0.1" in its frontmatter.
                    # - Body uses section headings to group concepts.
                    lines = content.splitlines()
                    if lines and lines[0].strip() == '---':
                        # Frontmatter is allowed ONLY at the root index.md
                        if file_path != output_dir / "index.md":
                            errors.append(f"Frontmatter is not permitted in non-root index.md at '{rel_file_path}'")
                        else:
                            # Parse frontmatter and ensure it's valid/contains okf_version
                            end_idx = -1
                            for i in range(1, len(lines)):
                                if lines[i].strip() == '---':
                                    end_idx = i
                                    break
                            if end_idx == -1:
                                errors.append(f"Malformed frontmatter delimiter in root index.md at '{rel_file_path}'")
                            else:
                                fm_text = "\n".join(lines[1:end_idx])
                                try:
                                    fm = yaml.safe_load(fm_text) or {}
                                    if "okf_version" not in fm:
                                        errors.append(f"Root index.md frontmatter missing 'okf_version' field at '{rel_file_path}'")
                                    elif str(fm["okf_version"]) != "0.1":
                                        errors.append(f"Unsupported 'okf_version' version '{fm['okf_version']}' in root index.md")
                                except Exception as e:
                                    errors.append(f"Failed to parse frontmatter of root index.md at '{rel_file_path}': {e}")
                                lines = lines[end_idx+1:]
                    
                    # Validate body of index.md: Should use section/group headings
                    body_text = "\n".join(lines)
                    headings = re.findall(r'^#\s+\S+', body_text, re.MULTILINE)
                    if not headings:
                        errors.append(f"Index file at '{rel_file_path}' must contain at least one section/group heading (e.g. '# Concepts')")
                        
                elif filename == "log.md":
                    # Validate log.md structure:
                    # - Flat list of date-grouped entries, newest first.
                    # - Date headings must use YYYY-MM-DD format.
                    # - No frontmatter.
                    if content.startswith('---'):
                        errors.append(f"Frontmatter is not permitted in log.md at '{rel_file_path}'")
                        
                    # Check for date headings
                    headings = re.findall(r'^##\s+(\d{4}-\d{2}-\d{2})', content, re.MULTILINE)
                    if not headings:
                        errors.append(f"Log file at '{rel_file_path}' must contain at least one ISO 8601 date heading in YYYY-MM-DD format (e.g. '## 2026-05-22')")
                        
                else:
                    # Concept Document:
                    # - Must contain a parseable YAML frontmatter block.
                    # - Frontmatter block contains a non-empty 'type' field.
                    lines = content.splitlines()
                    if not lines or lines[0].strip() != '---':
                        errors.append(f"Concept document '{rel_file_path}' must start with a YAML frontmatter delimiter '---'")
                        continue
                        
                    end_idx = -1
                    for i in range(1, len(lines)):
                        if lines[i].strip() == '---':
                            end_idx = i
                            break
                            
                    if end_idx == -1:
                        errors.append(f"Concept document '{rel_file_path}' has unmatched frontmatter delimiter")
                        continue
                        
                    fm_text = "\n".join(lines[1:end_idx])
                    try:
                        fm = yaml.safe_load(fm_text)
                    except Exception as e:
                        errors.append(f"Failed to parse frontmatter of concept document '{rel_file_path}': {e}")
                        continue
                        
                    if not isinstance(fm, dict):
                        errors.append(f"Concept document '{rel_file_path}' frontmatter is not a key-value mapping")
                        continue
                        
                    if 'type' not in fm or not str(fm['type']).strip():
                        errors.append(f"Concept document '{rel_file_path}' is missing required, non-empty 'type' frontmatter field")
                        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
