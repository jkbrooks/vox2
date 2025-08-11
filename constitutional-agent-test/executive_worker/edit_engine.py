from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List


@dataclass
class FileEdit:
    path: str
    original_substring: str
    replacement: str


class EditEngine:
    def __init__(self, root: str) -> None:
        self.root = root

    def apply_edits(self, edits: List[FileEdit]) -> None:
        backups: List[tuple[str, str]] = []
        try:
            for e in edits:
                target = os.path.join(self.root, e.path)
                
                # Handle file creation (empty original_substring means create/append)
                if not os.path.exists(target):
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    with open(target, "w", encoding="utf-8") as f:
                        f.write(e.replacement)
                    backups.append((target, ""))  # Empty backup for new file
                    continue
                
                # Handle existing file editing
                with open(target, "r", encoding="utf-8") as f:
                    content = f.read()
                
                backups.append((target, content))
                
                # If original_substring is empty, append content
                if e.original_substring == "":
                    new_content = content + e.replacement
                else:
                    if e.original_substring not in content:
                        # Special handling for module declarations in lib.rs
                        if e.path.endswith("lib.rs") and "pub mod" in e.replacement:
                            # Extract module name from replacement
                            import re
                            mod_match = re.search(r'pub mod (\w+);', e.replacement)
                            if mod_match:
                                module_name = mod_match.group(1)
                                # Check if module already exists
                                if f"pub mod {module_name};" not in content:
                                    # Add module declaration at the end
                                    new_content = content.rstrip() + f"\npub mod {module_name};\n"
                                else:
                                    # Module already exists, no change needed
                                    new_content = content
                            else:
                                raise RuntimeError(f"Context '{e.original_substring}' not found in {e.path}")
                        else:
                            raise RuntimeError(f"Context '{e.original_substring}' not found in {e.path}")
                    else:
                        new_content = content.replace(e.original_substring, e.replacement, 1)
                
                with open(target, "w", encoding="utf-8") as f:
                    f.write(new_content)
                    
        except Exception:
            # rollback
            for path, old in backups[::-1]:
                if old == "":  # New file, delete it
                    if os.path.exists(path):
                        os.remove(path)
                else:  # Existing file, restore content
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(old)
            raise
