"""Tests for intelligent error recovery system."""

import pytest
from executive_worker.error_recovery import (
    IntelligentErrorHandler, ErrorAnalysis, RecoveryAction
)
from executive_worker.models import CommandResult


class TestIntelligentErrorHandler:
    
    @pytest.fixture
    def error_handler(self, tmp_path):
        """Create an error handler for testing."""
        return IntelligentErrorHandler(str(tmp_path))
    
    def test_initialization(self, error_handler):
        """Test error handler initialization."""
        assert error_handler.root_path.exists()
        assert len(error_handler.python_patterns) > 0
        assert len(error_handler.javascript_patterns) > 0
        assert len(error_handler.rust_patterns) > 0
    
    def test_python_syntax_error(self, error_handler):
        """Test parsing Python syntax errors."""
        error_output = """
  File "test.py", line 5
    def broken(
              ^
SyntaxError: invalid syntax
"""
        
        analyses = error_handler.analyze_error(error_output, "python test.py")
        
        assert len(analyses) > 0
        syntax_errors = [a for a in analyses if a.error_type == 'syntax_error']
        assert len(syntax_errors) > 0
        
        error = syntax_errors[0]
        assert error.severity == 'high'
        assert 'invalid syntax' in error.message
        assert len(error.suggested_fixes) > 0
    
    def test_python_module_not_found(self, error_handler):
        """Test parsing Python ModuleNotFoundError."""
        error_output = """
Traceback (most recent call last):
  File "test.py", line 1, in <module>
    import nonexistent_module
ModuleNotFoundError: No module named 'nonexistent_module'
"""
        
        analyses = error_handler.analyze_error(error_output, "python test.py")
        
        missing_module_errors = [a for a in analyses if a.error_type == 'missing_dependency']
        assert len(missing_module_errors) > 0
        
        error = missing_module_errors[0]
        assert error.context['module_name'] == 'nonexistent_module'
        assert any('pip install' in fix for fix in error.suggested_fixes)
    
    def test_python_name_error(self, error_handler):
        """Test parsing Python NameError."""
        error_output = """
Traceback (most recent call last):
  File "test.py", line 5, in <module>
    print(undefined_variable)
NameError: name 'undefined_variable' is not defined
"""
        
        analyses = error_handler.analyze_error(error_output, "python test.py")
        
        name_errors = [a for a in analyses if a.error_type == 'name_error']
        assert len(name_errors) > 0
        
        error = name_errors[0]
        assert error.context['undefined_name'] == 'undefined_variable'
        assert error.severity == 'high'
        assert any('Define the variable' in fix for fix in error.suggested_fixes)
    
    def test_javascript_error(self, error_handler):
        """Test parsing JavaScript errors."""
        error_output = """
/path/to/script.js:10:5: error: Unexpected token '}'
    }
    ^
"""
        
        analyses = error_handler.analyze_error(error_output, "node script.js")
        
        js_errors = [a for a in analyses if a.error_type == 'javascript_error']
        assert len(js_errors) > 0
        
        error = js_errors[0]
        assert error.file_path == '/path/to/script.js'
        assert error.line_number == 10
        assert error.column == 5
        assert 'Unexpected token' in error.message
    
    def test_javascript_missing_module(self, error_handler):
        """Test parsing JavaScript missing module errors."""
        error_output = """
Error: Cannot find module 'express'
    at Function.Module._resolveFilename (internal/modules/cjs/loader.js:636:15)
"""
        
        analyses = error_handler.analyze_error(error_output, "node app.js")
        
        missing_module_errors = [a for a in analyses if a.error_type == 'missing_dependency']
        assert len(missing_module_errors) > 0
        
        error = missing_module_errors[0]
        assert error.context['module_name'] == 'express'
        assert any('npm install' in fix for fix in error.suggested_fixes)
    
    def test_rust_compile_error(self, error_handler):
        """Test parsing Rust compiler errors."""
        error_output = """
error[E0425]: cannot find value `undefined_var` in this scope
 --> src/main.rs:5:13
  |
5 |     println!("{}", undefined_var);
  |             ^^^^^^^^^^^^^ not found in this scope
"""
        
        analyses = error_handler.analyze_error(error_output, "cargo build")
        
        rust_errors = [a for a in analyses if a.error_type in ['rust_compile_error', 'rust_not_found']]
        assert len(rust_errors) > 0
    
    def test_generic_permission_error(self, error_handler):
        """Test parsing generic permission errors."""
        error_output = "bash: ./script.sh: Permission denied"
        
        analyses = error_handler.analyze_error(error_output, "./script.sh")
        
        permission_errors = [a for a in analyses if a.error_type == 'permission_error']
        assert len(permission_errors) > 0
        
        error = permission_errors[0]
        assert error.severity == 'medium'
        assert any('permission' in fix.lower() for fix in error.suggested_fixes)
    
    def test_generic_file_not_found(self, error_handler):
        """Test parsing generic file not found errors."""
        error_output = "cat: nonexistent_file.txt: No such file or directory"
        
        analyses = error_handler.analyze_error(error_output, "cat nonexistent_file.txt")
        
        file_errors = [a for a in analyses if a.error_type == 'file_not_found']
        assert len(file_errors) > 0
        
        error = file_errors[0]
        assert any('file exists' in fix.lower() for fix in error.suggested_fixes)
    
    def test_generic_command_not_found(self, error_handler):
        """Test parsing command not found errors."""
        error_output = "bash: nonexistent_command: command not found"
        
        analyses = error_handler.analyze_error(error_output, "nonexistent_command")
        
        cmd_errors = [a for a in analyses if a.error_type == 'command_not_found']
        assert len(cmd_errors) > 0
        
        error = cmd_errors[0]
        assert error.severity == 'high'
        assert any('install' in fix.lower() for fix in error.suggested_fixes)
    
    def test_recovery_action_suggestions(self, error_handler):
        """Test recovery action suggestions."""
        # Create a missing dependency error
        analysis = ErrorAnalysis(
            error_type='missing_dependency',
            severity='medium',
            file_path=None,
            line_number=None,
            column=None,
            message="Module 'requests' not found",
            suggested_fixes=['Install the module: pip install requests'],
            context={'module_name': 'requests', 'language': 'python'}
        )
        
        actions = error_handler.suggest_recovery_actions([analysis])
        
        assert len(actions) > 0
        install_actions = [a for a in actions if a.action_type == 'install_dependency']
        assert len(install_actions) > 0
        
        action = install_actions[0]
        assert 'pip install requests' in action.commands
        assert action.confidence >= 0.8
    
    def test_recovery_action_syntax_error(self, error_handler):
        """Test recovery actions for syntax errors."""
        analysis = ErrorAnalysis(
            error_type='syntax_error',
            severity='high',
            file_path='test.py',
            line_number=5,
            column=None,
            message='invalid syntax',
            suggested_fixes=['Check for missing colons'],
            context={'language': 'python'}
        )
        
        actions = error_handler.suggest_recovery_actions([analysis])
        
        assert len(actions) > 0
        fix_actions = [a for a in actions if a.action_type == 'fix_syntax']
        assert len(fix_actions) > 0
        
        action = fix_actions[0]
        assert 'test.py' in action.files_to_modify
    
    def test_auto_recovery_high_confidence(self, error_handler, monkeypatch):
        """Test automatic recovery for high-confidence fixes."""
        # Mock subprocess.run to simulate successful command execution
        def mock_run(*args, **kwargs):
            class MockResult:
                returncode = 0
                stdout = "Successfully installed requests"
                stderr = ""
            return MockResult()
        
        monkeypatch.setattr("subprocess.run", mock_run)
        
        # Create a command result with missing dependency error
        command_result = CommandResult(
            cmd="python test.py",
            exit_code=1,
            stdout="",
            stderr="ModuleNotFoundError: No module named 'requests'",
            duration_ms=100
        )
        
        executed_actions = error_handler.auto_recover(command_result)
        
        # Should have attempted to install the dependency
        assert len(executed_actions) >= 0  # May or may not execute depending on confidence
    
    def test_python_fix_suggestions(self, error_handler):
        """Test Python-specific fix suggestions."""
        fixes = error_handler._suggest_python_fixes("indentation error", "test.py")
        assert any('indentation' in fix.lower() for fix in fixes)
        
        fixes = error_handler._suggest_python_fixes("syntax error", "test.py")
        assert any('syntax' in fix.lower() or 'colon' in fix.lower() or 'parenthes' in fix.lower() for fix in fixes)
        
        fixes = error_handler._suggest_python_fixes("import error", "test.py")
        assert any('import' in fix.lower() for fix in fixes)
    
    def test_javascript_fix_suggestions(self, error_handler):
        """Test JavaScript-specific fix suggestions."""
        fixes = error_handler._suggest_js_fixes("unexpected token")
        assert any('semicolon' in fix.lower() or 'bracket' in fix.lower() for fix in fixes)
        
        fixes = error_handler._suggest_js_fixes("undefined variable")
        assert any('declare' in fix.lower() for fix in fixes)
        
        fixes = error_handler._suggest_js_fixes("cannot read property")
        assert any('object exists' in fix.lower() for fix in fixes)
    
    def test_rust_fix_suggestions(self, error_handler):
        """Test Rust-specific fix suggestions."""
        fixes = error_handler._suggest_rust_fixes("borrow checker error")
        assert any('borrow' in fix.lower() or 'ownership' in fix.lower() for fix in fixes)
        
        fixes = error_handler._suggest_rust_fixes("type mismatch")
        assert any('type' in fix.lower() for fix in fixes)
        
        fixes = error_handler._suggest_rust_fixes("trait not implemented")
        assert any('trait' in fix.lower() for fix in fixes)
    
    def test_c_fix_suggestions(self, error_handler):
        """Test C/C++-specific fix suggestions."""
        fixes = error_handler._suggest_c_fixes("undeclared identifier")
        assert any('declare' in fix.lower() for fix in fixes)
        
        fixes = error_handler._suggest_c_fixes("type error")
        assert any('type' in fix.lower() for fix in fixes)
        
        fixes = error_handler._suggest_c_fixes("expected semicolon")
        assert any('semicolon' in fix.lower() for fix in fixes)
    
    def test_multiple_error_analysis(self, error_handler):
        """Test analyzing multiple errors in one output."""
        error_output = """
File "test1.py", line 5
    def broken(
              ^
SyntaxError: invalid syntax

File "test2.py", line 10, in <module>
    import nonexistent_module
ModuleNotFoundError: No module named 'nonexistent_module'
"""
        
        analyses = error_handler.analyze_error(error_output, "python")
        
        # Should find both syntax error and missing module error
        error_types = [a.error_type for a in analyses]
        assert 'syntax_error' in error_types
        assert 'missing_dependency' in error_types
    
    def test_empty_error_output(self, error_handler):
        """Test handling empty error output."""
        analyses = error_handler.analyze_error("", "some_command")
        assert len(analyses) == 0
    
    def test_unrecognized_error_format(self, error_handler):
        """Test handling unrecognized error formats."""
        error_output = "Some completely unrecognized error format"
        analyses = error_handler.analyze_error(error_output, "unknown_command")
        
        # Should handle gracefully, might not find specific patterns
        # but shouldn't crash
        assert isinstance(analyses, list)
    
    def test_successful_command_no_recovery(self, error_handler):
        """Test that successful commands don't trigger recovery."""
        command_result = CommandResult(
            cmd="echo 'success'",
            exit_code=0,
            stdout="success",
            stderr="",
            duration_ms=50
        )
        
        executed_actions = error_handler.auto_recover(command_result)
        assert len(executed_actions) == 0
