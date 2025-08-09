"""Tests for enhanced codebase utilities."""

import pytest
import tempfile
import os
from pathlib import Path

from executive_worker.enhanced_codebase_utils import EnhancedCodebaseUtils, Symbol, Reference


class TestEnhancedCodebaseUtils:
    
    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            
            # Create test files
            python_file = workspace / "test_module.py"
            python_file.write_text("""
def hello_world():
    print("Hello, World!")

class TestClass:
    def method_one(self):
        return "method one"
    
    def method_two(self):
        return "method two"

import os
import sys
from pathlib import Path
""")
            
            js_file = workspace / "test_script.js"
            js_file.write_text("""
function greet(name) {
    return `Hello, ${name}!`;
}

class Calculator {
    add(a, b) {
        return a + b;
    }
}

import { someFunction } from './other_module';
export { greet, Calculator };
""")
            
            rust_file = workspace / "lib.rs"
            rust_file.write_text("""
pub fn main() {
    println!("Hello, Rust!");
}

pub struct Point {
    x: f64,
    y: f64,
}

use std::collections::HashMap;
""")
            
            yield str(workspace)
    
    def test_initialization(self, temp_workspace):
        """Test EnhancedCodebaseUtils initialization."""
        utils = EnhancedCodebaseUtils(temp_workspace)
        assert utils.root_path == Path(temp_workspace)
        assert utils.cache_dir.exists()
    
    def test_glob_files(self, temp_workspace):
        """Test file globbing with exclusions."""
        utils = EnhancedCodebaseUtils(temp_workspace)
        
        # Test basic globbing
        py_files = utils.glob_files("**/*.py")
        assert len(py_files) == 1
        assert py_files[0].endswith("test_module.py")
        
        # Test multiple patterns
        all_files = utils.glob_files("**/*")
        assert len(all_files) >= 3  # At least our test files
    
    def test_enhanced_grep(self, temp_workspace):
        """Test enhanced grep functionality."""
        utils = EnhancedCodebaseUtils(temp_workspace)
        
        # Search for a function definition
        results = utils.grep("def hello_world", context_lines=1)
        assert len(results) == 1
        
        result_file = list(results.keys())[0]
        matches = results[result_file]
        assert len(matches) == 1
        assert matches[0]['line_number'] == 2
        assert 'def hello_world' in matches[0]['line']
        assert len(matches[0]['context']) == 3  # 1 before + match + 1 after
    
    def test_python_file_parsing(self, temp_workspace):
        """Test Python file parsing for symbols."""
        utils = EnhancedCodebaseUtils(temp_workspace)
        
        python_file = str(Path(temp_workspace) / "test_module.py")
        file_info = utils.get_file_context(python_file)
        
        assert file_info['language'] == 'python'
        assert len(file_info['symbols']) >= 3  # hello_world, TestClass, method_one, method_two
        
        # Check for specific symbols
        symbol_names = [s.name for s in file_info['symbols']]
        assert 'hello_world' in symbol_names
        assert 'TestClass' in symbol_names
        assert 'method_one' in symbol_names
        
        # Check imports
        assert 'os' in file_info['imports']
        assert 'sys' in file_info['imports']
    
    def test_javascript_file_parsing(self, temp_workspace):
        """Test JavaScript file parsing for symbols."""
        utils = EnhancedCodebaseUtils(temp_workspace)
        
        js_file = str(Path(temp_workspace) / "test_script.js")
        file_info = utils.get_file_context(js_file)
        
        assert file_info['language'] == 'javascript'
        assert len(file_info['symbols']) >= 2  # greet, Calculator
        
        # Check for specific symbols
        symbol_names = [s.name for s in file_info['symbols']]
        assert 'greet' in symbol_names
        assert 'Calculator' in symbol_names
        
        # Check imports/exports
        assert len(file_info['imports']) > 0
        assert len(file_info['exports']) > 0
    
    def test_rust_file_parsing(self, temp_workspace):
        """Test Rust file parsing for symbols."""
        utils = EnhancedCodebaseUtils(temp_workspace)
        
        rust_file = str(Path(temp_workspace) / "lib.rs")
        file_info = utils.get_file_context(rust_file)
        
        assert file_info['language'] == 'rust'
        assert len(file_info['symbols']) >= 2  # main, Point
        
        # Check for specific symbols
        symbol_names = [s.name for s in file_info['symbols']]
        assert 'main' in symbol_names
        assert 'Point' in symbol_names
        
        # Check imports
        assert len(file_info['imports']) > 0
    
    def test_build_codebase_index(self, temp_workspace):
        """Test building comprehensive codebase index."""
        utils = EnhancedCodebaseUtils(temp_workspace)
        
        index_summary = utils.build_codebase_index()
        
        assert index_summary['processed_files'] >= 3
        assert index_summary['total_symbols'] > 0
        assert 'python' in index_summary['languages']
        assert 'javascript' in index_summary['languages']
        assert 'rust' in index_summary['languages']
        
        # Check that file cache is populated
        assert len(utils.file_cache) >= 3
    
    def test_semantic_search(self, temp_workspace):
        """Test semantic search functionality."""
        utils = EnhancedCodebaseUtils(temp_workspace)
        utils.build_codebase_index()
        
        # Search for a function
        results = utils.semantic_search("hello")
        assert len(results) > 0
        
        # Should find hello_world function
        found_hello = any('hello_world' in str(r.get('symbol', '')) for r in results)
        assert found_hello
        
        # Test with file type filtering
        py_results = utils.semantic_search("class", file_types=['.py'])
        assert len(py_results) > 0
    
    def test_find_definitions(self, temp_workspace):
        """Test finding symbol definitions."""
        utils = EnhancedCodebaseUtils(temp_workspace)
        utils.build_codebase_index()
        
        # Find class definitions
        class_defs = utils.find_definitions("TestClass")
        assert len(class_defs) > 0
        assert class_defs[0]['symbol'].kind == 'class'
        
        # Find function definitions
        func_defs = utils.find_definitions("hello_world")
        assert len(func_defs) > 0
        assert func_defs[0]['symbol'].kind == 'function'
    
    def test_analyze_dependencies(self, temp_workspace):
        """Test dependency analysis."""
        utils = EnhancedCodebaseUtils(temp_workspace)
        
        python_file = str(Path(temp_workspace) / "test_module.py")
        deps = utils.analyze_dependencies(python_file)
        
        # Should find external dependencies
        assert 'os' in deps['external_deps']
        assert 'sys' in deps['external_deps']
        
        # pathlib might be detected as external (simplified implementation)
        # In a real implementation, this would be more sophisticated
    
    def test_workspace_summary(self, temp_workspace):
        """Test enhanced workspace summary."""
        utils = EnhancedCodebaseUtils(temp_workspace)
        
        summary = utils.workspace_summary()
        
        assert "Enhanced Workspace Analysis" in summary
        assert "Total files:" in summary
        assert "Total symbols:" in summary
        # Check for file extensions instead of language names
        assert ".py" in summary
        assert ".js" in summary  
        assert ".rs" in summary
    
    def test_candidate_eoi_paths(self, temp_workspace):
        """Test enhanced EOI path detection."""
        utils = EnhancedCodebaseUtils(temp_workspace)
        
        # Create some additional important files
        readme = Path(temp_workspace) / "README.md"
        readme.write_text("# Test Project")
        
        main_py = Path(temp_workspace) / "main.py"
        main_py.write_text("def main(): pass")
        
        candidates = utils.candidate_eoi_paths()
        
        # Should include important files
        candidate_names = [os.path.basename(c) for c in candidates]
        assert "README.md" in candidate_names
        assert "main.py" in candidate_names
        
        # Should also include files with many symbols (check for any Python file)
        assert any(c.endswith(".py") for c in candidates)
    
    def test_relevance_scoring(self, temp_workspace):
        """Test relevance scoring for semantic search."""
        utils = EnhancedCodebaseUtils(temp_workspace)
        
        # Test exact match
        score1 = utils._calculate_relevance_score("hello_world", "def hello_world():", "hello_world")
        assert score1 >= 10.0  # Exact match gets high score
        
        # Test partial match
        score2 = utils._calculate_relevance_score("hello_world", "def hello_world():", "hello")
        assert 0 < score2 < 10.0
        
        # Test no match
        score3 = utils._calculate_relevance_score("hello_world", "def hello_world():", "xyz")
        assert score3 == 0.0
    
    def test_language_detection(self, temp_workspace):
        """Test programming language detection."""
        utils = EnhancedCodebaseUtils(temp_workspace)
        
        assert utils._detect_language("test.py") == "python"
        assert utils._detect_language("test.js") == "javascript"
        assert utils._detect_language("test.ts") == "typescript"
        assert utils._detect_language("test.rs") == "rust"
        assert utils._detect_language("test.java") == "java"
        assert utils._detect_language("test.unknown") == "unknown"
    
    def test_internal_module_detection(self, temp_workspace):
        """Test internal vs external module detection."""
        utils = EnhancedCodebaseUtils(temp_workspace)
        
        # Create a local module
        local_module = Path(temp_workspace) / "local_module.py"
        local_module.write_text("# Local module")
        
        assert utils._is_internal_module("local_module") == True
        assert utils._is_internal_module("os") == False
        assert utils._is_internal_module("nonexistent") == False
    
    def test_caching(self, temp_workspace):
        """Test caching functionality."""
        utils = EnhancedCodebaseUtils(temp_workspace)
        
        # Build index to populate cache
        utils.build_codebase_index()
        
        # Check that cache is populated
        assert len(utils.file_cache) > 0
        
        # Database should exist
        assert utils.db_path.exists()
    
    @pytest.mark.skipif(not hasattr(EnhancedCodebaseUtils, 'build_dependency_graph'), 
                       reason="NetworkX not available")
    def test_dependency_graph(self, temp_workspace):
        """Test dependency graph building (if NetworkX available)."""
        utils = EnhancedCodebaseUtils(temp_workspace)
        utils.build_codebase_index()
        
        graph_info = utils.build_dependency_graph()
        
        if 'error' not in graph_info:
            assert 'nodes' in graph_info
            assert 'edges' in graph_info
            assert graph_info['nodes'] > 0
