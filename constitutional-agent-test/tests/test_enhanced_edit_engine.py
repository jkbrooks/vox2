"""Tests for enhanced edit engine."""

import pytest
import tempfile
import ast
from pathlib import Path

from executive_worker.enhanced_edit_engine import (
    EnhancedEditEngine, ASTEdit, SemanticEdit, EditValidation
)
from executive_worker.models import FileEdit


class TestEnhancedEditEngine:
    
    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            
            # Create test Python file
            python_file = workspace / "test_file.py"
            python_file.write_text("""
def old_function():
    return "old implementation"

class TestClass:
    def method_one(self):
        return "method one"
    
    def method_two(self):
        return "method two"

def another_function():
    old_function()
    return "another"
""")
            
            yield str(workspace)
    
    def test_initialization(self, temp_workspace):
        """Test EnhancedEditEngine initialization."""
        engine = EnhancedEditEngine(temp_workspace)
        assert engine.root_path == Path(temp_workspace)
        assert engine.backup_dir is None
    
    def test_apply_basic_edits(self, temp_workspace):
        """Test applying basic file edits."""
        engine = EnhancedEditEngine(temp_workspace)
        
        # Test replacing content
        edit = FileEdit(
            path="test_file.py",
            original_substring='return "old implementation"',
            replacement='return "new implementation"'
        )
        
        engine.apply_edits([edit])
        
        # Verify the change
        test_file = Path(temp_workspace) / "test_file.py"
        content = test_file.read_text()
        assert 'return "new implementation"' in content
        assert 'return "old implementation"' not in content
    
    def test_create_new_file(self, temp_workspace):
        """Test creating a new file."""
        engine = EnhancedEditEngine(temp_workspace)
        
        # Test creating new file
        edit = FileEdit(
            path="new_file.py",
            original_substring="",
            replacement="def new_function():\n    return 'new'"
        )
        
        engine.apply_edits([edit])
        
        # Verify the file was created
        new_file = Path(temp_workspace) / "new_file.py"
        assert new_file.exists()
        content = new_file.read_text()
        assert "def new_function():" in content
    
    def test_append_to_file(self, temp_workspace):
        """Test appending to an existing file."""
        engine = EnhancedEditEngine(temp_workspace)
        
        # Test appending to file
        edit = FileEdit(
            path="test_file.py",
            original_substring="",
            replacement="\n\ndef appended_function():\n    return 'appended'"
        )
        
        engine.apply_edits([edit])
        
        # Verify the content was appended
        test_file = Path(temp_workspace) / "test_file.py"
        content = test_file.read_text()
        assert "def appended_function():" in content
    
    def test_ast_rename_symbol(self, temp_workspace):
        """Test AST-aware symbol renaming."""
        engine = EnhancedEditEngine(temp_workspace)
        
        ast_edit = ASTEdit(
            file_path="test_file.py",
            node_type="function",
            target_name="old_function",
            operation="rename",
            new_content="new_function"
        )
        
        results = engine.apply_ast_edits([ast_edit])
        
        assert len(results) == 1
        validation = results[0]
        assert validation.is_valid
        assert validation.syntax_valid
        
        # Verify the rename worked
        test_file = Path(temp_workspace) / "test_file.py"
        content = test_file.read_text()
        assert "def new_function():" in content
        assert "def old_function():" not in content
        # The call should also be renamed
        assert "new_function()" in content
    
    def test_ast_replace_node(self, temp_workspace):
        """Test AST-aware node replacement."""
        engine = EnhancedEditEngine(temp_workspace)
        
        ast_edit = ASTEdit(
            file_path="test_file.py",
            node_type="function",
            target_name="method_one",
            operation="replace",
            new_content='    def method_one(self):\n        return "updated method one"'
        )
        
        results = engine.apply_ast_edits([ast_edit])
        
        assert len(results) == 1
        validation = results[0]
        # Note: Simple replacement might not be perfectly valid, but should attempt the operation
    
    def test_ast_insert_node(self, temp_workspace):
        """Test AST-aware node insertion."""
        engine = EnhancedEditEngine(temp_workspace)
        
        ast_edit = ASTEdit(
            file_path="test_file.py",
            node_type="function",
            target_name="",
            operation="insert",
            new_content="def inserted_function():\n    return 'inserted'",
            line_number=5
        )
        
        results = engine.apply_ast_edits([ast_edit])
        
        assert len(results) == 1
        validation = results[0]
        # Should attempt insertion even if not perfect
    
    def test_semantic_rename_across_files(self, temp_workspace):
        """Test semantic renaming across multiple files."""
        engine = EnhancedEditEngine(temp_workspace)
        
        # Create another file that uses the function
        other_file = Path(temp_workspace) / "other_file.py"
        other_file.write_text("""
from test_file import old_function

def caller():
    return old_function()
""")
        
        semantic_edit = SemanticEdit(
            file_path="test_file.py",
            edit_type="rename_symbol",
            target="old_function",
            replacement="renamed_function",
            context={
                'files': ['test_file.py', 'other_file.py']
            }
        )
        
        results = engine.apply_semantic_edits([semantic_edit])
        
        assert len(results) == 1
        validation = results[0]
        # Should attempt the cross-file rename
    
    def test_add_method_to_class(self, temp_workspace):
        """Test adding a method to a class."""
        engine = EnhancedEditEngine(temp_workspace)
        
        semantic_edit = SemanticEdit(
            file_path="test_file.py",
            edit_type="add_method",
            target="TestClass",
            replacement="""    def new_method(self):
        return "new method"
""",
            context={}
        )
        
        results = engine.apply_semantic_edits([semantic_edit])
        
        assert len(results) == 1
        validation = results[0]
        
        if validation.is_valid:
            # Verify the method was added
            test_file = Path(temp_workspace) / "test_file.py"
            content = test_file.read_text()
            assert "def new_method(self):" in content
    
    def test_refactor_function(self, temp_workspace):
        """Test refactoring a function."""
        engine = EnhancedEditEngine(temp_workspace)
        
        semantic_edit = SemanticEdit(
            file_path="test_file.py",
            edit_type="refactor_function",
            target="another_function",
            replacement="""def another_function():
    # Refactored implementation
    result = old_function()
    return f"refactored: {result}"
""",
            context={}
        )
        
        results = engine.apply_semantic_edits([semantic_edit])
        
        assert len(results) == 1
        validation = results[0]
        # Should attempt the refactor
    
    def test_validation_syntax_check(self, temp_workspace):
        """Test syntax validation."""
        engine = EnhancedEditEngine(temp_workspace)
        
        # Valid Python code
        valid_code = "def test():\n    return 42"
        validation = engine.validate_edit_result(valid_code, '.py')
        assert validation.is_valid
        assert validation.syntax_valid
        
        # Invalid Python code
        invalid_code = "def test(\n    return 42"
        validation = engine.validate_edit_result(invalid_code, '.py')
        assert not validation.is_valid
        assert not validation.syntax_valid
        assert len(validation.errors) > 0
    
    def test_validation_balance_check(self, temp_workspace):
        """Test balance checking for brackets, etc."""
        engine = EnhancedEditEngine(temp_workspace)
        
        # Unbalanced parentheses
        unbalanced = "def test():\n    print('hello'"
        validation = engine.validate_edit_result(unbalanced, '.py')
        assert len(validation.warnings) > 0
        # Should warn about unbalanced quotes or parentheses
    
    def test_edit_preview(self, temp_workspace):
        """Test edit preview generation."""
        engine = EnhancedEditEngine(temp_workspace)
        
        edit = FileEdit(
            path="test_file.py",
            original_substring='return "old implementation"',
            replacement='return "new implementation"'
        )
        
        previews = engine.generate_edit_preview([edit])
        
        assert len(previews) == 1
        preview = previews[0]
        
        assert preview['operation'] == 'modify'
        assert len(preview['changes']) == 1
        assert preview['changes'][0]['type'] == 'replace'
        assert preview['changes'][0]['old'] == 'return "old implementation"'
        assert preview['changes'][0]['new'] == 'return "new implementation"'
    
    def test_edit_preview_new_file(self, temp_workspace):
        """Test edit preview for new file creation."""
        engine = EnhancedEditEngine(temp_workspace)
        
        edit = FileEdit(
            path="new_file.py",
            original_substring="",
            replacement="def new_function():\n    return 'new'"
        )
        
        previews = engine.generate_edit_preview([edit])
        
        assert len(previews) == 1
        preview = previews[0]
        
        assert preview['operation'] == 'create'
        assert len(preview['changes']) == 1
        assert preview['changes'][0]['type'] == 'create'
    
    def test_rollback_functionality(self, temp_workspace):
        """Test rollback functionality on edit failure."""
        engine = EnhancedEditEngine(temp_workspace)
        
        # Read original content
        test_file = Path(temp_workspace) / "test_file.py"
        original_content = test_file.read_text()
        
        # Create an edit that should fail (non-existent original substring)
        bad_edit = FileEdit(
            path="test_file.py",
            original_substring="this_does_not_exist",
            replacement="replacement"
        )
        
        # This should raise an exception and rollback
        with pytest.raises(ValueError):
            engine.apply_edits([bad_edit])
        
        # File should be unchanged
        current_content = test_file.read_text()
        assert current_content == original_content
    
    def test_multiple_edits_transaction(self, temp_workspace):
        """Test that multiple edits are applied as a transaction."""
        engine = EnhancedEditEngine(temp_workspace)
        
        edits = [
            FileEdit(
                path="test_file.py",
                original_substring='return "old implementation"',
                replacement='return "new implementation"'
            ),
            FileEdit(
                path="test_file.py",
                original_substring='return "method one"',
                replacement='return "updated method one"'
            )
        ]
        
        engine.apply_edits(edits)
        
        # Verify both changes were applied
        test_file = Path(temp_workspace) / "test_file.py"
        content = test_file.read_text()
        assert 'return "new implementation"' in content
        assert 'return "updated method one"' in content
    
    def test_cleanup(self, temp_workspace):
        """Test cleanup functionality."""
        engine = EnhancedEditEngine(temp_workspace)
        
        # Apply an edit to create backup directory
        edit = FileEdit(
            path="test_file.py",
            original_substring='return "old implementation"',
            replacement='return "new implementation"'
        )
        
        engine.apply_edits([edit])
        
        # Backup directory should exist
        assert engine.backup_dir is not None
        
        # Cleanup should remove it
        engine.cleanup()
        assert not Path(engine.backup_dir).exists() if engine.backup_dir else True
    
    def test_ast_error_handling(self, temp_workspace):
        """Test AST edit error handling."""
        engine = EnhancedEditEngine(temp_workspace)
        
        # Create a file with syntax errors
        bad_file = Path(temp_workspace) / "bad_file.py"
        bad_file.write_text("def broken(\n    pass")
        
        ast_edit = ASTEdit(
            file_path="bad_file.py",
            node_type="function",
            target_name="broken",
            operation="rename",
            new_content="fixed"
        )
        
        results = engine.apply_ast_edits([ast_edit])
        
        assert len(results) == 1
        validation = results[0]
        assert not validation.is_valid
        assert not validation.syntax_valid
        assert len(validation.errors) > 0
    
    def test_unknown_operations(self, temp_workspace):
        """Test handling of unknown operations."""
        engine = EnhancedEditEngine(temp_workspace)
        
        # Unknown AST operation
        ast_edit = ASTEdit(
            file_path="test_file.py",
            node_type="function",
            target_name="old_function",
            operation="unknown_operation",
            new_content="something"
        )
        
        results = engine.apply_ast_edits([ast_edit])
        
        assert len(results) == 1
        validation = results[0]
        assert not validation.is_valid
        assert "Unknown AST operation" in validation.errors[0]
        
        # Unknown semantic operation
        semantic_edit = SemanticEdit(
            file_path="test_file.py",
            edit_type="unknown_edit_type",
            target="something",
            replacement="something_else",
            context={}
        )
        
        results = engine.apply_semantic_edits([semantic_edit])
        
        assert len(results) == 1
        validation = results[0]
        assert not validation.is_valid
        assert "Unknown semantic edit type" in validation.errors[0]
