import os
import re
import datetime
import yaml
from pathlib import Path
from ..base import BasePublisherTarget

class OKFPublisher(BasePublisherTarget):
    def generate(self, bundle: dict, output_dir: Path) -> None:
        """
        Generates the OKF directory structure and files.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        title = bundle.get("title", "Knowledge Bundle")

        # 1. Build concept map for resolving wikilinks
        # Map lowercase stems, paths, and paths without .md to bundle-relative absolute paths
        concept_map = {}
        for path in bundle.get("content", {}).keys():
            stem = Path(path).stem
            rel_path = f"/{path.lstrip('/')}"
            concept_map[stem.lower()] = rel_path
            concept_map[path.lower()] = rel_path
            if path.lower().endswith('.md'):
                concept_map[path.lower()[:-3]] = rel_path

        # 2. Write concept documents
        for path, content in bundle.get("content", {}).items():
            # Ensure path is relative and safe from directory traversal
            rel_path = path.lstrip('/')
            note_path = (output_dir / rel_path).resolve()
            if not note_path.is_relative_to(output_dir.resolve()):
                raise ValueError(f"Path traversal detected in bundle content path: {path}")

            # Ensure parent directories exist
            note_path.parent.mkdir(parents=True, exist_ok=True)

            # Process frontmatter, default title, type, and convert wikilinks
            processed_content = self._process_concept(content, Path(path).stem, concept_map)
            note_path.write_text(processed_content, encoding="utf-8")

        # 3. Generate log.md at the bundle root
        log_path = output_dir / "log.md"
        today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
        log_content = (
            "# Bundle Update Log\n\n"
            f"## {today}\n"
            "* **Creation**: Initialized the Open Knowledge Format bundle.\n"
        )
        log_path.write_text(log_content, encoding="utf-8")

        # 4. Generate progressive index.md files for all directories
        self._generate_indices(output_dir, title)

    def _process_concept(self, content: str, default_title: str, concept_map: dict[str, str]) -> str:
        """
        Parses frontmatter of a concept document, adds/updates the required 'type' field,
        retains other YAML fields, converts wikilinks to standard markdown links,
        and returns the updated markdown text.
        """
        frontmatter = {}
        body = content

        # Check if content starts with frontmatter delimiter
        lines = content.splitlines(keepends=True)
        if lines and lines[0].strip() == '---':
            end_idx = -1
            for i in range(1, len(lines)):
                if lines[i].strip() == '---':
                    end_idx = i
                    break
            if end_idx != -1:
                fm_text = "".join(lines[1:end_idx])
                body = "".join(lines[end_idx+1:])
                try:
                    frontmatter = yaml.safe_load(fm_text) or {}
                except Exception:
                    frontmatter = {}

        # Enforce type constraint
        if 'type' not in frontmatter or not frontmatter['type']:
            frontmatter['type'] = 'Concept'

        # Set human-readable display name if omitted
        if 'title' not in frontmatter or not frontmatter['title']:
            frontmatter['title'] = default_title

        # Set timestamp if omitted
        if 'timestamp' not in frontmatter:
            frontmatter['timestamp'] = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Re-serialize frontmatter
        fm_dump = yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False).strip()

        # Convert Wikilinks [[Target]] or [[Target|Alias]] in the body
        def replace_wikilink(match):
            link_content = match.group(1)
            parts = link_content.split('|', 1)
            target = parts[0].strip()
            alias = parts[1].strip() if len(parts) > 1 else target

            # Strip .md suffix if present in the target to resolve stem
            target_stem = target
            if target_stem.lower().endswith('.md'):
                target_stem = target_stem[:-3]

            target_stem_lower = target_stem.lower()
            if target_stem_lower in concept_map:
                resolved_link = concept_map[target_stem_lower]
            else:
                # If target looks like a filename/path, keep it, otherwise format to bundle-relative
                if '/' in target or target.endswith('.md'):
                    resolved_link = f"/{target.lstrip('/')}"
                else:
                    resolved_link = f"/{target}.md"

            return f"[{alias}]({resolved_link})"

        updated_body = re.sub(r'\[\[(.*?)\]\]', replace_wikilink, body)

        return f"---\n{fm_dump}\n---\n{updated_body}"

    def _generate_indices(self, output_dir: Path, bundle_title: str) -> None:
        """
        Walks directories inside output_dir and creates progressive index.md files.
        """
        dirs_to_index = set()
        dirs_to_index.add(output_dir)
        for root, dirs, files in os.walk(output_dir):
            root_path = Path(root)
            if any(part.startswith('.') for part in root_path.relative_to(output_dir).parts):
                continue
            dirs_to_index.add(root_path)
            for d in dirs:
                if not d.startswith('.'):
                    dirs_to_index.add(root_path / d)

        # Process deepest directories first so subdirectory checks work correctly
        for d in sorted(dirs_to_index, key=lambda x: len(x.parts), reverse=True):
            concepts_in_dir = []
            subdirs_in_dir = []

            for item in d.iterdir():
                if item.is_file():
                    if item.name in ["index.md", "log.md"] or not item.name.endswith(".md"):
                        continue
                    concepts_in_dir.append(item)
                elif item.is_dir():
                    if item.name.startswith('.'):
                        continue
                    # Include if the subdirectory contains a generated index.md
                    if (item / "index.md").exists():
                        subdirs_in_dir.append(item)

            if not concepts_in_dir and not subdirs_in_dir:
                continue

            index_content = []
            # Add version frontmatter ONLY to bundle root index.md
            if d == output_dir:
                index_content.append("---")
                index_content.append('okf_version: "0.1"')
                index_content.append("---")
                index_content.append(f"# {bundle_title}")
            else:
                index_content.append(f"# {d.name.title()} Directory")

            index_content.append("")

            if concepts_in_dir:
                index_content.append("# Concepts")
                index_content.append("")
                concepts_in_dir.sort(key=lambda x: x.name.lower())
                for c_path in concepts_in_dir:
                    c_title = c_path.stem
                    c_desc = ""
                    try:
                        c_text = c_path.read_text(encoding="utf-8")
                        lines = c_text.splitlines()
                        if lines and lines[0].strip() == '---':
                            end_idx = -1
                            for idx in range(1, len(lines)):
                                if lines[idx].strip() == '---':
                                    end_idx = idx
                                    break
                            if end_idx != -1:
                                fm = yaml.safe_load("\n".join(lines[1:end_idx])) or {}
                                c_title = fm.get("title", c_title)
                                c_desc = fm.get("description", "")
                    except Exception:
                        pass

                    rel_link = c_path.name
                    desc_part = f" - {c_desc}" if c_desc else ""
                    index_content.append(f"* [{c_title}]({rel_link}){desc_part}")
                index_content.append("")

            if subdirs_in_dir:
                index_content.append("# Subdirectories")
                index_content.append("")
                subdirs_in_dir.sort(key=lambda x: x.name.lower())
                for s_dir in subdirs_in_dir:
                    s_name = s_dir.name
                    index_content.append(f"* [{s_name.title()}]({s_name}/)")
                index_content.append("")

            index_path = d / "index.md"
            index_path.write_text("\n".join(index_content), encoding="utf-8")

    def validate(self, output_dir: Path) -> dict:
        from .validator import OKFValidator
        return OKFValidator().validate(output_dir)
