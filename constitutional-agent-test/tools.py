"""
Minimal tool layer for Constitutional Agent
Provides essential capabilities for working with real codebases
"""

import os
import subprocess
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

@dataclass
class CommandResult:
    """Result from command execution"""
    stdout: str
    stderr: str
    return_code: int
    success: bool

@dataclass 
class FileMatch:
    """A search match in a file"""
    file_path: str
    line_number: int
    line_content: str

class FileTools:
    """File operations for the agent"""
    
    def __init__(self, workspace_root: str = "."):
        self.workspace_root = Path(workspace_root).resolve()
    
    def read_file(self, path: str) -> str:
        """Read a file"""
        full_path = self._resolve_path(path)
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return full_path.read_text()
    
    def write_file(self, path: str, content: str) -> bool:
        """Write content to a file"""
        full_path = self._resolve_path(path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)
        return True
    
    def edit_file(self, path: str, old_content: str, new_content: str) -> bool:
        """Replace content in a file"""
        current = self.read_file(path)
        if old_content not in current:
            raise ValueError(f"Content not found in {path}")
        updated = current.replace(old_content, new_content, 1)
        self.write_file(path, updated)
        return True
    
    def search_files(self, pattern: str, file_glob: str = "**/*.rs") -> List[FileMatch]:
        """Search for pattern in files"""
        matches = []
        for file_path in self.workspace_root.glob(file_glob):
            if file_path.is_file():
                try:
                    content = file_path.read_text()
                    for i, line in enumerate(content.splitlines(), 1):
                        if pattern in line:
                            matches.append(FileMatch(
                                file_path=str(file_path.relative_to(self.workspace_root)),
                                line_number=i,
                                line_content=line.strip()
                            ))
                except:
                    continue
        return matches
    
    def list_files(self, pattern: str = "**/*.rs") -> List[str]:
        """List files matching pattern"""
        files = []
        for file_path in self.workspace_root.glob(pattern):
            if file_path.is_file():
                files.append(str(file_path.relative_to(self.workspace_root)))
        return sorted(files)
    
    def _resolve_path(self, path: str) -> Path:
        """Resolve path relative to workspace"""
        p = Path(path)
        return p if p.is_absolute() else self.workspace_root / p

class CommandTools:
    """Command execution for the agent"""
    
    def __init__(self, workspace_root: str = "."):
        self.workspace_root = Path(workspace_root).resolve()
    
    def run_command(self, command: str, timeout: int = 30) -> CommandResult:
        """Run a shell command"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return CommandResult(
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode,
                success=result.returncode == 0
            )
        except subprocess.TimeoutExpired:
            return CommandResult(
                stdout="",
                stderr=f"Command timed out after {timeout} seconds",
                return_code=-1,
                success=False
            )
        except Exception as e:
            return CommandResult(
                stdout="",
                stderr=str(e),
                return_code=-1,
                success=False
            )
    
    def run_cargo_build(self) -> CommandResult:
        """Build Rust project"""
        return self.run_command("cargo build")
    
    def run_cargo_test(self, test_name: Optional[str] = None) -> CommandResult:
        """Run Rust tests"""
        cmd = f"cargo test {test_name}" if test_name else "cargo test"
        return self.run_command(cmd)
    
    def run_cargo_check(self) -> CommandResult:
        """Check Rust project for errors"""
        return self.run_command("cargo check")

class CodebaseTools:
    """Tools for understanding codebase structure"""
    
    def __init__(self, workspace_root: str = "."):
        self.workspace_root = Path(workspace_root).resolve()
        self.file_tools = FileTools(workspace_root)
    
    def analyze_structure(self) -> Dict:
        """Analyze project structure"""
        structure = {
            "root": str(self.workspace_root),
            "has_cargo": (self.workspace_root / "Cargo.toml").exists(),
            "rust_files": [],
            "test_files": [],
            "directories": []
        }
        
        # Find Rust files
        structure["rust_files"] = self.file_tools.list_files("**/*.rs")
        
        # Find test files
        for file_path in structure["rust_files"]:
            if "test" in file_path or file_path.startswith("tests/"):
                structure["test_files"].append(file_path)
        
        # Find key directories
        for dir_path in self.workspace_root.iterdir():
            if dir_path.is_dir() and not dir_path.name.startswith('.'):
                structure["directories"].append(dir_path.name)
        
        return structure
    
    def find_relevant_files(self, task_description: str) -> List[str]:
        """Find files relevant to a task"""
        relevant = []
        
        # Extract keywords from task
        keywords = re.findall(r'\b[A-Za-z]+\b', task_description)
        keywords = [k for k in keywords if len(k) > 3]  # Filter short words
        
        # Search for keywords
        for keyword in keywords:
            matches = self.file_tools.search_files(keyword, "**/*.rs")
            for match in matches:
                if match.file_path not in relevant:
                    relevant.append(match.file_path)
        
        return relevant[:10]  # Limit to avoid overwhelming context
