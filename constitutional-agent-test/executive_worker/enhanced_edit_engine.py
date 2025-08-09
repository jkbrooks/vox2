"""Enhanced edit engine with AST-awareness and validation capabilities."""

import os
import ast
import tempfile
import shutil
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path
from dataclasses import dataclass

from .models import FileEdit


@dataclass
class ASTEdit:
    """AST-aware edit operation."""
    file_path: str
    node_type: str  # 'function', 'class', 'import', etc.
    target_name: str  # name of symbol to edit
    operation: str  # 'rename', 'replace', 'insert', 'delete'
    new_content: str
    line_number: Optional[int] = None


@dataclass
class SemanticEdit:
    """High-level semantic edit operation."""
    file_path: str
    edit_type: str  # 'rename_symbol', 'add_method', 'refactor_function'
    target: str
    replacement: str
    context: Dict[str, Any]


@dataclass
class EditValidation:
    """Result of edit validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    syntax_valid: bool


class EnhancedEditEngine:
    """Enhanced edit engine with AST awareness and validation."""
    
    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.backup_dir = None
        
    def apply_edits(self, edits: List[FileEdit]) -> None:
        """Apply file edits with enhanced validation and rollback."""
        # Create backup directory
        self.backup_dir = tempfile.mkdtemp(prefix="edit_backup_")
        backups = []
        
        try:
            for edit in edits:
                target_path = Path(edit.path)
                if not target_path.is_absolute():
                    target_path = self.root_path / edit.path
                
                # Backup original file
                if target_path.exists():
                    backup_path = Path(self.backup_dir) / f"{target_path.name}.backup"
                    shutil.copy2(target_path, backup_path)
                    backups.append((target_path, backup_path))
                else:
                    backups.append((target_path, None))
                
                # Apply edit
                self._apply_single_edit(edit, target_path)
                
        except Exception as e:
            # Rollback all changes
            self._rollback_edits(backups)
            raise e
    
    def _apply_single_edit(self, edit: FileEdit, target_path: Path):
        """Apply a single file edit."""
        # Ensure directory exists
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not target_path.exists():
            # Create new file
            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(edit.replacement)
        else:
            # Edit existing file
            with open(target_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if edit.original_substring == "":
                # Append to file
                new_content = content + edit.replacement
            else:
                # Replace content
                if edit.original_substring not in content:
                    raise ValueError(f"Original substring not found in {target_path}")
                new_content = content.replace(edit.original_substring, edit.replacement, 1)
            
            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
    
    def apply_ast_edits(self, edits: List[ASTEdit]) -> List[EditValidation]:
        """Apply AST-aware edits with syntax validation."""
        results = []
        
        for edit in edits:
            try:
                validation = self._apply_ast_edit(edit)
                results.append(validation)
            except Exception as e:
                results.append(EditValidation(
                    is_valid=False,
                    errors=[str(e)],
                    warnings=[],
                    syntax_valid=False
                ))
        
        return results
    
    def _apply_ast_edit(self, edit: ASTEdit) -> EditValidation:
        """Apply a single AST-aware edit."""
        file_path = Path(edit.file_path)
        if not file_path.is_absolute():
            file_path = self.root_path / edit.file_path
        
        # Read and parse the file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            return EditValidation(
                is_valid=False,
                errors=[f"Syntax error in original file: {e}"],
                warnings=[],
                syntax_valid=False
            )
        
        # Apply the edit based on operation type
        if edit.operation == 'rename':
            new_content = self._rename_symbol_in_ast(content, tree, edit.target_name, edit.new_content)
        elif edit.operation == 'replace':
            new_content = self._replace_node_in_ast(content, tree, edit.target_name, edit.new_content)
        elif edit.operation == 'insert':
            new_content = self._insert_node_in_ast(content, tree, edit.new_content, edit.line_number)
        elif edit.operation == 'delete':
            new_content = self._delete_node_in_ast(content, tree, edit.target_name)
        else:
            return EditValidation(
                is_valid=False,
                errors=[f"Unknown AST operation: {edit.operation}"],
                warnings=[],
                syntax_valid=False
            )
        
        # Validate the new content
        validation = self.validate_edit_result(new_content, file_path.suffix)
        
        if validation.is_valid:
            # Write the new content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
        
        return validation
    
    def _rename_symbol_in_ast(self, content: str, tree: ast.AST, old_name: str, new_name: str) -> str:
        """Rename a symbol throughout the AST."""
        class SymbolRenamer(ast.NodeTransformer):
            def visit_Name(self, node):
                if node.id == old_name:
                    node.id = new_name
                return node
            
            def visit_FunctionDef(self, node):
                if node.name == old_name:
                    node.name = new_name
                return self.generic_visit(node)
            
            def visit_ClassDef(self, node):
                if node.name == old_name:
                    node.name = new_name
                return self.generic_visit(node)
        
        new_tree = SymbolRenamer().visit(tree)
        return ast.unparse(new_tree)
    
    def _replace_node_in_ast(self, content: str, tree: ast.AST, target_name: str, new_content: str) -> str:
        """Replace a node in the AST."""
        # This is a simplified implementation
        # In practice, you'd need more sophisticated AST manipulation
        lines = content.splitlines()
        
        # Find the target node and replace its content
        for node in ast.walk(tree):
            if hasattr(node, 'name') and node.name == target_name:
                if hasattr(node, 'lineno'):
                    # Simple line replacement (could be more sophisticated)
                    lines[node.lineno - 1] = new_content
                    break
        
        return '\n'.join(lines)
    
    def _insert_node_in_ast(self, content: str, tree: ast.AST, new_content: str, line_number: Optional[int]) -> str:
        """Insert new content into the AST."""
        lines = content.splitlines()
        
        if line_number is None:
            # Append at end
            lines.append(new_content)
        else:
            # Insert at specific line
            lines.insert(line_number - 1, new_content)
        
        return '\n'.join(lines)
    
    def _delete_node_in_ast(self, content: str, tree: ast.AST, target_name: str) -> str:
        """Delete a node from the AST."""
        lines = content.splitlines()
        
        # Find and remove the target node
        for node in ast.walk(tree):
            if hasattr(node, 'name') and node.name == target_name:
                if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
                    # Remove lines for this node
                    start_line = node.lineno - 1
                    end_line = node.end_lineno
                    del lines[start_line:end_line]
                    break
        
        return '\n'.join(lines)
    
    def apply_semantic_edits(self, edits: List[SemanticEdit]) -> List[EditValidation]:
        """Apply high-level semantic edits."""
        results = []
        
        for edit in edits:
            try:
                validation = self._apply_semantic_edit(edit)
                results.append(validation)
            except Exception as e:
                results.append(EditValidation(
                    is_valid=False,
                    errors=[str(e)],
                    warnings=[],
                    syntax_valid=False
                ))
        
        return results
    
    def _apply_semantic_edit(self, edit: SemanticEdit) -> EditValidation:
        """Apply a single semantic edit."""
        if edit.edit_type == 'rename_symbol':
            return self._rename_symbol_across_files(edit.target, edit.replacement, edit.context)
        elif edit.edit_type == 'add_method':
            return self._add_method_to_class(edit.file_path, edit.target, edit.replacement)
        elif edit.edit_type == 'refactor_function':
            return self._refactor_function(edit.file_path, edit.target, edit.replacement)
        else:
            return EditValidation(
                is_valid=False,
                errors=[f"Unknown semantic edit type: {edit.edit_type}"],
                warnings=[],
                syntax_valid=False
            )
    
    def _rename_symbol_across_files(self, old_name: str, new_name: str, context: Dict[str, Any]) -> EditValidation:
        """Rename a symbol across multiple files."""
        errors = []
        warnings = []
        
        # Get files to modify from context
        files_to_modify = context.get('files', [])
        
        for file_path in files_to_modify:
            try:
                ast_edit = ASTEdit(
                    file_path=file_path,
                    node_type='name',
                    target_name=old_name,
                    operation='rename',
                    new_content=new_name
                )
                validation = self._apply_ast_edit(ast_edit)
                if not validation.is_valid:
                    errors.extend(validation.errors)
                warnings.extend(validation.warnings)
            except Exception as e:
                errors.append(f"Error renaming in {file_path}: {e}")
        
        return EditValidation(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            syntax_valid=True
        )
    
    def _add_method_to_class(self, file_path: str, class_name: str, method_code: str) -> EditValidation:
        """Add a method to a class."""
        try:
            full_path = Path(file_path)
            if not full_path.is_absolute():
                full_path = self.root_path / file_path
            
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            # Find the class and add the method
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == class_name:
                    # Parse the new method
                    method_ast = ast.parse(method_code).body[0]
                    node.body.append(method_ast)
                    break
            
            new_content = ast.unparse(tree)
            validation = self.validate_edit_result(new_content, full_path.suffix)
            
            if validation.is_valid:
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
            
            return validation
            
        except Exception as e:
            return EditValidation(
                is_valid=False,
                errors=[str(e)],
                warnings=[],
                syntax_valid=False
            )
    
    def _refactor_function(self, file_path: str, function_name: str, new_implementation: str) -> EditValidation:
        """Refactor a function with new implementation."""
        try:
            full_path = Path(file_path)
            if not full_path.is_absolute():
                full_path = self.root_path / file_path
            
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Simple replacement for now (could be more sophisticated with AST)
            lines = content.splitlines()
            in_function = False
            function_indent = 0
            start_line = None
            end_line = None
            
            for i, line in enumerate(lines):
                if line.strip().startswith(f'def {function_name}('):
                    in_function = True
                    start_line = i
                    function_indent = len(line) - len(line.lstrip())
                elif in_function and line.strip() and len(line) - len(line.lstrip()) <= function_indent and not line.startswith(' '):
                    end_line = i
                    break
            
            if start_line is not None:
                if end_line is None:
                    end_line = len(lines)
                
                # Replace function
                lines[start_line:end_line] = new_implementation.splitlines()
                new_content = '\n'.join(lines)
                
                validation = self.validate_edit_result(new_content, full_path.suffix)
                
                if validation.is_valid:
                    with open(full_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                
                return validation
            else:
                return EditValidation(
                    is_valid=False,
                    errors=[f"Function {function_name} not found"],
                    warnings=[],
                    syntax_valid=False
                )
                
        except Exception as e:
            return EditValidation(
                is_valid=False,
                errors=[str(e)],
                warnings=[],
                syntax_valid=False
            )
    
    def validate_edit_result(self, content: str, file_extension: str) -> EditValidation:
        """Validate the result of an edit operation."""
        errors = []
        warnings = []
        syntax_valid = True
        
        # Language-specific validation
        if file_extension == '.py':
            try:
                ast.parse(content)
            except SyntaxError as e:
                errors.append(f"Python syntax error: {e}")
                syntax_valid = False
        elif file_extension in ['.js', '.ts']:
            # Could add JavaScript/TypeScript validation here
            # For now, just basic checks
            if 'function(' in content and ')' not in content:
                warnings.append("Possible missing closing parenthesis")
        elif file_extension == '.rs':
            # Could add Rust validation here
            pass
        
        # General checks
        if not content.strip():
            warnings.append("File is empty after edit")
        
        # Check for common issues
        if content.count('(') != content.count(')'):
            warnings.append("Unbalanced parentheses")
        if content.count('{') != content.count('}'):
            warnings.append("Unbalanced braces")
        if content.count('[') != content.count(']'):
            warnings.append("Unbalanced brackets")
        
        return EditValidation(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            syntax_valid=syntax_valid
        )
    
    def generate_edit_preview(self, edits: List[FileEdit]) -> List[Dict[str, Any]]:
        """Generate a preview of what edits will do."""
        previews = []
        
        for edit in edits:
            target_path = Path(edit.path)
            if not target_path.is_absolute():
                target_path = self.root_path / edit.path
            
            preview = {
                'file_path': str(target_path),
                'operation': 'create' if not target_path.exists() else 'modify',
                'original_content': '',
                'new_content': edit.replacement,
                'changes': []
            }
            
            if target_path.exists():
                with open(target_path, 'r', encoding='utf-8') as f:
                    original = f.read()
                    preview['original_content'] = original
                    
                    if edit.original_substring:
                        # Show the specific change
                        preview['changes'] = [{
                            'type': 'replace',
                            'old': edit.original_substring,
                            'new': edit.replacement
                        }]
                    else:
                        # Append operation
                        preview['changes'] = [{
                            'type': 'append',
                            'content': edit.replacement
                        }]
            else:
                preview['changes'] = [{
                    'type': 'create',
                    'content': edit.replacement
                }]
            
            previews.append(preview)
        
        return previews
    
    def _rollback_edits(self, backups: List[Tuple[Path, Optional[Path]]]):
        """Rollback edits using backups."""
        for target_path, backup_path in backups:
            try:
                if backup_path and backup_path.exists():
                    shutil.copy2(backup_path, target_path)
                elif target_path.exists():
                    # File was created, remove it
                    target_path.unlink()
            except Exception as e:
                print(f"Error rolling back {target_path}: {e}")
    
    def cleanup(self):
        """Clean up temporary backup directory."""
        if self.backup_dir and os.path.exists(self.backup_dir):
            shutil.rmtree(self.backup_dir)
            self.backup_dir = None
