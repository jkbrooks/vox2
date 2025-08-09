"""Intelligent error parsing and recovery mechanisms."""

import re
import subprocess
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from pathlib import Path

from .models import CommandResult


@dataclass
class ErrorAnalysis:
    """Analysis of an error condition."""
    error_type: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    file_path: Optional[str]
    line_number: Optional[int]
    column: Optional[int]
    message: str
    suggested_fixes: List[str]
    context: Dict[str, Any]


@dataclass
class RecoveryAction:
    """A suggested recovery action."""
    action_type: str  # 'fix_syntax', 'install_dependency', 'create_file', etc.
    description: str
    commands: List[str]
    files_to_modify: List[str]
    confidence: float  # 0.0 to 1.0


class IntelligentErrorHandler:
    """Intelligent error parsing and recovery system."""
    
    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        
        # Error pattern matchers
        self.python_patterns = [
            (r'File "([^"]+)", line (\d+)', self._parse_python_error),
            (r'SyntaxError: (.+)', self._parse_syntax_error),
            (r'ModuleNotFoundError: No module named \'([^\']+)\'', self._parse_missing_module),
            (r'ImportError: (.+)', self._parse_import_error),
            (r'AttributeError: (.+)', self._parse_attribute_error),
            (r'NameError: name \'([^\']+)\' is not defined', self._parse_name_error),
        ]
        
        self.javascript_patterns = [
            (r'(.+):(\d+):(\d+): (.+)', self._parse_js_error),
            (r'Cannot find module \'([^\']+)\'', self._parse_js_missing_module),
            (r'ReferenceError: (.+)', self._parse_js_reference_error),
        ]
        
        self.rust_patterns = [
            (r'error\[E\d+\]: (.+)', self._parse_rust_error),
            (r'--> ([^:]+):(\d+):(\d+)', self._parse_rust_location),
            (r'cannot find (.+) in (.+)', self._parse_rust_not_found),
        ]
        
        self.compiler_patterns = [
            (r'(.+):(\d+):(\d+): error: (.+)', self._parse_gcc_error),
            (r'fatal error: (.+): No such file or directory', self._parse_missing_header),
        ]
    
    def analyze_error(self, error_output: str, command: str = "", file_context: Optional[str] = None) -> List[ErrorAnalysis]:
        """Analyze error output and provide structured analysis."""
        analyses = []
        
        # Determine error context from command
        if 'python' in command.lower() or '.py' in command:
            analyses.extend(self._analyze_python_errors(error_output))
        elif 'node' in command.lower() or 'npm' in command.lower() or '.js' in command or '.ts' in command:
            analyses.extend(self._analyze_javascript_errors(error_output))
        elif 'cargo' in command.lower() or 'rustc' in command.lower():
            analyses.extend(self._analyze_rust_errors(error_output))
        elif any(compiler in command.lower() for compiler in ['gcc', 'g++', 'clang']):
            analyses.extend(self._analyze_compiler_errors(error_output))
        else:
            # Generic error analysis
            analyses.extend(self._analyze_generic_errors(error_output))
        
        return analyses
    
    def _analyze_python_errors(self, error_output: str) -> List[ErrorAnalysis]:
        """Analyze Python-specific errors."""
        analyses = []
        
        for pattern, parser in self.python_patterns:
            matches = re.finditer(pattern, error_output, re.MULTILINE)
            for match in matches:
                analysis = parser(match, error_output)
                if analysis:
                    analyses.append(analysis)
        
        return analyses
    
    def _parse_python_error(self, match, full_output: str) -> Optional[ErrorAnalysis]:
        """Parse general Python error with file and line info."""
        file_path = match.group(1)
        line_number = int(match.group(2))
        
        # Extract error message from context
        lines = full_output.split('\n')
        error_line = None
        for line in lines:
            if file_path in line and str(line_number) in line:
                # Find the actual error message
                idx = lines.index(line)
                if idx + 1 < len(lines):
                    error_line = lines[idx + 1].strip()
                break
        
        return ErrorAnalysis(
            error_type='python_runtime',
            severity='medium',
            file_path=file_path,
            line_number=line_number,
            column=None,
            message=error_line or "Python runtime error",
            suggested_fixes=self._suggest_python_fixes(error_line or "", file_path),
            context={'full_traceback': full_output}
        )
    
    def _parse_syntax_error(self, match, full_output: str) -> Optional[ErrorAnalysis]:
        """Parse Python syntax errors."""
        message = match.group(1)
        
        suggested_fixes = []
        if 'invalid syntax' in message:
            suggested_fixes.append("Check for missing colons, parentheses, or quotes")
        elif 'unexpected EOF' in message:
            suggested_fixes.append("Check for unclosed parentheses, brackets, or quotes")
        elif 'indentation' in message.lower():
            suggested_fixes.append("Fix indentation - use consistent spaces or tabs")
        
        return ErrorAnalysis(
            error_type='syntax_error',
            severity='high',
            file_path=None,
            line_number=None,
            column=None,
            message=message,
            suggested_fixes=suggested_fixes,
            context={'language': 'python'}
        )
    
    def _parse_missing_module(self, match, full_output: str) -> Optional[ErrorAnalysis]:
        """Parse missing module errors."""
        module_name = match.group(1)
        
        suggested_fixes = [
            f"Install the module: pip install {module_name}",
            f"Add {module_name} to requirements.txt",
            "Check if the module name is correct"
        ]
        
        return ErrorAnalysis(
            error_type='missing_dependency',
            severity='medium',
            file_path=None,
            line_number=None,
            column=None,
            message=f"Module '{module_name}' not found",
            suggested_fixes=suggested_fixes,
            context={'module_name': module_name, 'language': 'python'}
        )
    
    def _parse_import_error(self, match, full_output: str) -> Optional[ErrorAnalysis]:
        """Parse import errors."""
        message = match.group(1)
        
        suggested_fixes = [
            "Check if the imported module exists",
            "Verify the import path is correct",
            "Ensure the module is installed"
        ]
        
        return ErrorAnalysis(
            error_type='import_error',
            severity='medium',
            file_path=None,
            line_number=None,
            column=None,
            message=message,
            suggested_fixes=suggested_fixes,
            context={'language': 'python'}
        )
    
    def _parse_attribute_error(self, match, full_output: str) -> Optional[ErrorAnalysis]:
        """Parse attribute errors."""
        message = match.group(1)
        
        suggested_fixes = [
            "Check if the attribute name is spelled correctly",
            "Verify the object has the expected attribute",
            "Check the object type and available methods"
        ]
        
        return ErrorAnalysis(
            error_type='attribute_error',
            severity='medium',
            file_path=None,
            line_number=None,
            column=None,
            message=message,
            suggested_fixes=suggested_fixes,
            context={'language': 'python'}
        )
    
    def _parse_name_error(self, match, full_output: str) -> Optional[ErrorAnalysis]:
        """Parse name errors."""
        name = match.group(1)
        
        suggested_fixes = [
            f"Define the variable '{name}' before using it",
            f"Check if '{name}' is spelled correctly",
            f"Import '{name}' if it's from another module"
        ]
        
        return ErrorAnalysis(
            error_type='name_error',
            severity='high',
            file_path=None,
            line_number=None,
            column=None,
            message=f"Name '{name}' is not defined",
            suggested_fixes=suggested_fixes,
            context={'undefined_name': name, 'language': 'python'}
        )
    
    def _analyze_javascript_errors(self, error_output: str) -> List[ErrorAnalysis]:
        """Analyze JavaScript/TypeScript errors."""
        analyses = []
        
        for pattern, parser in self.javascript_patterns:
            matches = re.finditer(pattern, error_output, re.MULTILINE)
            for match in matches:
                analysis = parser(match, error_output)
                if analysis:
                    analyses.append(analysis)
        
        return analyses
    
    def _parse_js_error(self, match, full_output: str) -> Optional[ErrorAnalysis]:
        """Parse general JavaScript error."""
        file_path = match.group(1)
        line_number = int(match.group(2))
        column = int(match.group(3))
        message = match.group(4)
        
        return ErrorAnalysis(
            error_type='javascript_error',
            severity='medium',
            file_path=file_path,
            line_number=line_number,
            column=column,
            message=message,
            suggested_fixes=self._suggest_js_fixes(message),
            context={'language': 'javascript'}
        )
    
    def _parse_js_missing_module(self, match, full_output: str) -> Optional[ErrorAnalysis]:
        """Parse missing JavaScript module."""
        module_name = match.group(1)
        
        suggested_fixes = [
            f"Install the module: npm install {module_name}",
            f"Check if the module path is correct",
            "Verify the module exists in node_modules"
        ]
        
        return ErrorAnalysis(
            error_type='missing_dependency',
            severity='medium',
            file_path=None,
            line_number=None,
            column=None,
            message=f"Cannot find module '{module_name}'",
            suggested_fixes=suggested_fixes,
            context={'module_name': module_name, 'language': 'javascript'}
        )
    
    def _parse_js_reference_error(self, match, full_output: str) -> Optional[ErrorAnalysis]:
        """Parse JavaScript reference error."""
        message = match.group(1)
        
        suggested_fixes = [
            "Check if the variable is declared",
            "Verify the variable scope",
            "Check for typos in variable names"
        ]
        
        return ErrorAnalysis(
            error_type='reference_error',
            severity='high',
            file_path=None,
            line_number=None,
            column=None,
            message=message,
            suggested_fixes=suggested_fixes,
            context={'language': 'javascript'}
        )
    
    def _analyze_rust_errors(self, error_output: str) -> List[ErrorAnalysis]:
        """Analyze Rust compiler errors."""
        analyses = []
        
        for pattern, parser in self.rust_patterns:
            matches = re.finditer(pattern, error_output, re.MULTILINE)
            for match in matches:
                analysis = parser(match, error_output)
                if analysis:
                    analyses.append(analysis)
        
        return analyses
    
    def _parse_rust_error(self, match, full_output: str) -> Optional[ErrorAnalysis]:
        """Parse Rust compiler error."""
        message = match.group(1)
        
        return ErrorAnalysis(
            error_type='rust_compile_error',
            severity='high',
            file_path=None,
            line_number=None,
            column=None,
            message=message,
            suggested_fixes=self._suggest_rust_fixes(message),
            context={'language': 'rust'}
        )
    
    def _parse_rust_location(self, match, full_output: str) -> Optional[ErrorAnalysis]:
        """Parse Rust error location."""
        file_path = match.group(1)
        line_number = int(match.group(2))
        column = int(match.group(3))
        
        return ErrorAnalysis(
            error_type='rust_location',
            severity='medium',
            file_path=file_path,
            line_number=line_number,
            column=column,
            message="Rust error at this location",
            suggested_fixes=[],
            context={'language': 'rust'}
        )
    
    def _parse_rust_not_found(self, match, full_output: str) -> Optional[ErrorAnalysis]:
        """Parse Rust 'not found' errors."""
        item = match.group(1)
        location = match.group(2)
        
        suggested_fixes = [
            f"Add the missing {item}",
            f"Check the spelling of {item}",
            f"Import {item} if it's from another module"
        ]
        
        return ErrorAnalysis(
            error_type='rust_not_found',
            severity='high',
            file_path=None,
            line_number=None,
            column=None,
            message=f"Cannot find {item} in {location}",
            suggested_fixes=suggested_fixes,
            context={'missing_item': item, 'location': location, 'language': 'rust'}
        )
    
    def _analyze_compiler_errors(self, error_output: str) -> List[ErrorAnalysis]:
        """Analyze C/C++ compiler errors."""
        analyses = []
        
        for pattern, parser in self.compiler_patterns:
            matches = re.finditer(pattern, error_output, re.MULTILINE)
            for match in matches:
                analysis = parser(match, error_output)
                if analysis:
                    analyses.append(analysis)
        
        return analyses
    
    def _parse_gcc_error(self, match, full_output: str) -> Optional[ErrorAnalysis]:
        """Parse GCC/Clang error."""
        file_path = match.group(1)
        line_number = int(match.group(2))
        column = int(match.group(3))
        message = match.group(4)
        
        return ErrorAnalysis(
            error_type='compile_error',
            severity='high',
            file_path=file_path,
            line_number=line_number,
            column=column,
            message=message,
            suggested_fixes=self._suggest_c_fixes(message),
            context={'language': 'c/c++'}
        )
    
    def _parse_missing_header(self, match, full_output: str) -> Optional[ErrorAnalysis]:
        """Parse missing header file error."""
        header = match.group(1)
        
        suggested_fixes = [
            f"Create the header file {header}",
            f"Install the library containing {header}",
            f"Check the include path for {header}"
        ]
        
        return ErrorAnalysis(
            error_type='missing_header',
            severity='high',
            file_path=None,
            line_number=None,
            column=None,
            message=f"Header file '{header}' not found",
            suggested_fixes=suggested_fixes,
            context={'header_file': header, 'language': 'c/c++'}
        )
    
    def _analyze_generic_errors(self, error_output: str) -> List[ErrorAnalysis]:
        """Analyze generic errors."""
        analyses = []
        
        # Common patterns
        if 'permission denied' in error_output.lower():
            analyses.append(ErrorAnalysis(
                error_type='permission_error',
                severity='medium',
                file_path=None,
                line_number=None,
                column=None,
                message="Permission denied",
                suggested_fixes=["Check file permissions", "Run with appropriate privileges"],
                context={}
            ))
        
        if 'no such file or directory' in error_output.lower():
            analyses.append(ErrorAnalysis(
                error_type='file_not_found',
                severity='medium',
                file_path=None,
                line_number=None,
                column=None,
                message="File or directory not found",
                suggested_fixes=["Check if the file exists", "Verify the path is correct"],
                context={}
            ))
        
        if 'command not found' in error_output.lower():
            analyses.append(ErrorAnalysis(
                error_type='command_not_found',
                severity='high',
                file_path=None,
                line_number=None,
                column=None,
                message="Command not found",
                suggested_fixes=["Install the required tool", "Check PATH environment variable"],
                context={}
            ))
        
        return analyses
    
    def suggest_recovery_actions(self, analyses: List[ErrorAnalysis]) -> List[RecoveryAction]:
        """Suggest recovery actions based on error analyses."""
        actions = []
        
        for analysis in analyses:
            if analysis.error_type == 'missing_dependency':
                if analysis.context.get('language') == 'python':
                    module_name = analysis.context.get('module_name', '')
                    actions.append(RecoveryAction(
                        action_type='install_dependency',
                        description=f"Install Python module {module_name}",
                        commands=[f"pip install {module_name}"],
                        files_to_modify=[],
                        confidence=0.8
                    ))
                elif analysis.context.get('language') == 'javascript':
                    module_name = analysis.context.get('module_name', '')
                    actions.append(RecoveryAction(
                        action_type='install_dependency',
                        description=f"Install Node.js module {module_name}",
                        commands=[f"npm install {module_name}"],
                        files_to_modify=[],
                        confidence=0.8
                    ))
            
            elif analysis.error_type == 'syntax_error':
                actions.append(RecoveryAction(
                    action_type='fix_syntax',
                    description="Fix syntax error",
                    commands=[],
                    files_to_modify=[analysis.file_path] if analysis.file_path else [],
                    confidence=0.6
                ))
            
            elif analysis.error_type == 'file_not_found':
                actions.append(RecoveryAction(
                    action_type='create_file',
                    description="Create missing file",
                    commands=[],
                    files_to_modify=[],
                    confidence=0.5
                ))
            
            elif analysis.error_type == 'command_not_found':
                actions.append(RecoveryAction(
                    action_type='install_tool',
                    description="Install missing command-line tool",
                    commands=[],
                    files_to_modify=[],
                    confidence=0.7
                ))
        
        return actions
    
    def auto_recover(self, command_result: CommandResult) -> List[RecoveryAction]:
        """Attempt automatic recovery from command failure."""
        if command_result.exit_code == 0:
            return []
        
        # Analyze the error
        analyses = self.analyze_error(command_result.stderr, command_result.cmd)
        
        # Get recovery suggestions
        actions = self.suggest_recovery_actions(analyses)
        
        # Execute high-confidence automatic fixes
        executed_actions = []
        for action in actions:
            if action.confidence >= 0.8 and action.action_type in ['install_dependency']:
                try:
                    for cmd in action.commands:
                        result = subprocess.run(
                            cmd.split(),
                            capture_output=True,
                            text=True,
                            cwd=self.root_path
                        )
                        if result.returncode == 0:
                            executed_actions.append(action)
                except Exception as e:
                    print(f"Failed to execute recovery action: {e}")
        
        return executed_actions
    
    def _suggest_python_fixes(self, error_message: str, file_path: str) -> List[str]:
        """Suggest Python-specific fixes."""
        fixes = []
        
        if 'indentation' in error_message.lower():
            fixes.append("Fix indentation - use consistent spaces or tabs")
        if 'syntax' in error_message.lower():
            fixes.append("Check for missing colons, parentheses, or quotes")
        if 'import' in error_message.lower():
            fixes.append("Check import statements and module names")
        
        return fixes
    
    def _suggest_js_fixes(self, error_message: str) -> List[str]:
        """Suggest JavaScript-specific fixes."""
        fixes = []
        
        if 'unexpected token' in error_message.lower():
            fixes.append("Check for missing semicolons or brackets")
        if 'undefined' in error_message.lower():
            fixes.append("Declare the variable before using it")
        if 'cannot read property' in error_message.lower():
            fixes.append("Check if the object exists before accessing properties")
        
        return fixes
    
    def _suggest_rust_fixes(self, error_message: str) -> List[str]:
        """Suggest Rust-specific fixes."""
        fixes = []
        
        if 'borrow checker' in error_message.lower():
            fixes.append("Review ownership and borrowing rules")
        if 'type mismatch' in error_message.lower():
            fixes.append("Check type annotations and conversions")
        if 'trait' in error_message.lower():
            fixes.append("Implement required traits or import them")
        
        return fixes
    
    def _suggest_c_fixes(self, error_message: str) -> List[str]:
        """Suggest C/C++-specific fixes."""
        fixes = []
        
        if 'undeclared' in error_message.lower():
            fixes.append("Declare the variable or function")
        if 'type' in error_message.lower():
            fixes.append("Check type compatibility")
        if 'semicolon' in error_message.lower():
            fixes.append("Add missing semicolon")
        
        return fixes
