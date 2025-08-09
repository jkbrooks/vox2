"""Enhanced codebase utilities with Aider-inspired features for searching, indexing, and understanding code structure."""

import os
import glob
import sqlite3
import ast
import time
import hashlib
from collections import defaultdict, Counter, namedtuple
from typing import List, Dict, Set, Optional, Tuple, Any, NamedTuple
from pathlib import Path
import tempfile
import shutil

try:
    # Try to import tree-sitter for AST parsing (like Aider)
    from tree_sitter import Language, Parser, Node
    from grep_ast import TreeContext, filename_to_lang
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False


# Data structures for code understanding
Symbol = namedtuple("Symbol", "name kind file_path line_number definition_text")
Reference = namedtuple("Reference", "name file_path line_number context")
FileInfo = namedtuple("FileInfo", "path size mtime language symbols references")


class EnhancedCodebaseUtils:
    """Enhanced codebase utilities with semantic search, symbol tracking, and intelligent indexing."""
    
    def __init__(self, root_path: str, cache_dir: Optional[str] = None):
        self.root_path = Path(root_path)
        self.cache_dir = Path(cache_dir) if cache_dir else self.root_path / ".aider_cache"
        self.cache_dir.mkdir(exist_ok=True)
        
        # Initialize caches
        self.symbol_cache = {}
        self.file_cache = {}
        self.dependency_graph = defaultdict(set)
        
        # Setup SQLite cache (inspired by Aider)
        self.db_path = self.cache_dir / "codebase.db"
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for caching."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS file_symbols (
                        file_path TEXT PRIMARY KEY,
                        mtime REAL,
                        symbols TEXT,
                        symbol_references TEXT
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS file_dependencies (
                        source_file TEXT,
                        target_file TEXT,
                        relationship TEXT,
                        PRIMARY KEY (source_file, target_file)
                    )
                """)
        except sqlite3.Error as e:
            print(f"Database initialization error: {e}")
    
    def glob_files(self, pattern: str, exclude_patterns: List[str] = None) -> List[str]:
        """Find files matching a glob pattern, with exclusions."""
        exclude_patterns = exclude_patterns or [
            "**/.git/**", "**/node_modules/**", "**/__pycache__/**", 
            "**/target/**", "**/build/**", "**/.cache/**", "**/.aider_cache/**"
        ]
        
        full_pattern = str(self.root_path / pattern)
        matches = glob.glob(full_pattern, recursive=True)
        
        # Filter out excluded patterns
        filtered = []
        for match in matches:
            rel_path = os.path.relpath(match, self.root_path)
            excluded = False
            for exclude_pattern in exclude_patterns:
                if self._matches_pattern(rel_path, exclude_pattern):
                    excluded = True
                    break
            if not excluded and os.path.isfile(match):
                filtered.append(match)
        
        return filtered
    
    def _matches_pattern(self, path: str, pattern: str) -> bool:
        """Check if path matches glob pattern."""
        import fnmatch
        return fnmatch.fnmatch(path, pattern)
    
    def grep(self, pattern: str, file_paths: List[str] = None, context_lines: int = 2) -> Dict[str, List[Dict]]:
        """Enhanced grep with context and metadata."""
        if not file_paths:
            file_paths = self.glob_files("**/*")
        
        results = {}
        for file_path in file_paths:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    matches = []
                    for i, line in enumerate(lines):
                        if pattern in line:
                            # Get context lines
                            start = max(0, i - context_lines)
                            end = min(len(lines), i + context_lines + 1)
                            context = lines[start:end]
                            
                            matches.append({
                                'line_number': i + 1,
                                'line': line.strip(),
                                'context': [l.strip() for l in context],
                                'match_start': start + 1,
                                'match_end': end
                            })
                    
                    if matches:
                        results[file_path] = matches
            except (UnicodeDecodeError, PermissionError, FileNotFoundError):
                continue
        
        return results
    
    def semantic_search(self, query: str, file_types: List[str] = None, max_results: int = 50) -> List[Dict]:
        """Semantic search across the codebase using symbol understanding."""
        results = []
        query_lower = query.lower()
        
        # Search through cached symbols
        for file_path, file_info in self.file_cache.items():
            if file_types and not any(file_path.endswith(ft) for ft in file_types):
                continue
            
            # Score symbols based on relevance
            for symbol in file_info.get('symbols', []):
                score = self._calculate_relevance_score(symbol.name, symbol.definition_text, query_lower)
                if score > 0:
                    results.append({
                        'file_path': file_path,
                        'symbol': symbol,
                        'score': score,
                        'type': 'symbol'
                    })
            
            # Also search in references
            for ref in file_info.get('references', []):
                score = self._calculate_relevance_score(ref.name, ref.context, query_lower)
                if score > 0:
                    results.append({
                        'file_path': file_path,
                        'reference': ref,
                        'score': score * 0.7,  # References score lower than definitions
                        'type': 'reference'
                    })
        
        # Sort by relevance and limit results
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:max_results]
    
    def _calculate_relevance_score(self, name: str, text: str, query: str) -> float:
        """Calculate relevance score for semantic search."""
        score = 0.0
        name_lower = name.lower()
        text_lower = text.lower()
        
        # Exact name match gets highest score
        if name_lower == query:
            score += 10.0
        elif query in name_lower:
            score += 5.0
        
        # Partial matches in text
        if query in text_lower:
            score += 2.0
        
        # Word boundary matches
        query_words = query.split()
        for word in query_words:
            if word in name_lower:
                score += 1.0
            if word in text_lower:
                score += 0.5
        
        return score
    
    def find_definitions(self, symbol: str, file_types: List[str] = None) -> List[Dict]:
        """Find all definitions of a symbol."""
        results = []
        symbol_lower = symbol.lower()
        
        for file_path, file_info in self.file_cache.items():
            if file_types and not any(file_path.endswith(ft) for ft in file_types):
                continue
            
            for sym in file_info.get('symbols', []):
                if sym.kind in ['def', 'class', 'function'] and symbol_lower in sym.name.lower():
                    results.append({
                        'file_path': file_path,
                        'symbol': sym,
                        'line_number': sym.line_number,
                        'definition': sym.definition_text
                    })
        
        return results
    
    def find_usages(self, symbol: str, file_types: List[str] = None) -> List[Dict]:
        """Find all usages/references of a symbol."""
        results = []
        symbol_lower = symbol.lower()
        
        for file_path, file_info in self.file_cache.items():
            if file_types and not any(file_path.endswith(ft) for ft in file_types):
                continue
            
            for ref in file_info.get('references', []):
                if symbol_lower in ref.name.lower():
                    results.append({
                        'file_path': file_path,
                        'reference': ref,
                        'line_number': ref.line_number,
                        'context': ref.context
                    })
        
        return results
    
    def get_file_context(self, filepath: str, lines_around: int = 10) -> Dict:
        """Get rich context information about a file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Basic file info
            file_info = {
                'path': filepath,
                'size': len(content),
                'lines': len(content.splitlines()),
                'language': self._detect_language(filepath),
                'symbols': [],
                'imports': [],
                'exports': []
            }
            
            # Parse symbols if possible
            if filepath.endswith('.py'):
                file_info.update(self._parse_python_file(filepath, content))
            elif filepath.endswith(('.js', '.ts')):
                file_info.update(self._parse_javascript_file(filepath, content))
            elif filepath.endswith('.rs'):
                file_info.update(self._parse_rust_file(filepath, content))
            
            return file_info
            
        except Exception as e:
            return {'path': filepath, 'error': str(e)}
    
    def analyze_dependencies(self, filepath: str) -> Dict:
        """Analyze file dependencies and relationships."""
        dependencies = {
            'imports': [],
            'exports': [],
            'internal_deps': [],
            'external_deps': []
        }
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if filepath.endswith('.py'):
                dependencies.update(self._analyze_python_dependencies(content))
            elif filepath.endswith(('.js', '.ts')):
                dependencies.update(self._analyze_javascript_dependencies(content))
            elif filepath.endswith('.rs'):
                dependencies.update(self._analyze_rust_dependencies(content))
        
        except Exception:
            pass
        
        return dependencies
    
    def _parse_python_file(self, filepath: str, content: str) -> Dict:
        """Parse Python file for symbols and structure."""
        symbols = []
        imports = []
        exports = []
        references = []
        
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    symbols.append(Symbol(
                        name=node.name,
                        kind='function',
                        file_path=filepath,
                        line_number=node.lineno,
                        definition_text=f"def {node.name}(...)"
                    ))
                elif isinstance(node, ast.ClassDef):
                    symbols.append(Symbol(
                        name=node.name,
                        kind='class',
                        file_path=filepath,
                        line_number=node.lineno,
                        definition_text=f"class {node.name}:"
                    ))
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
                elif isinstance(node, ast.Name):
                    # Track name references
                    references.append(Reference(
                        name=node.id,
                        file_path=filepath,
                        line_number=node.lineno,
                        context=f"reference to {node.id}"
                    ))
        
        except SyntaxError:
            pass
        
        return {'symbols': symbols, 'imports': imports, 'exports': exports, 'references': references}
    
    def _parse_javascript_file(self, filepath: str, content: str) -> Dict:
        """Basic JavaScript/TypeScript parsing."""
        symbols = []
        imports = []
        exports = []
        references = []
        
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            line = line.strip()
            
            # Simple regex-based parsing (could be enhanced with proper AST)
            if line.startswith('function '):
                name = line.split('(')[0].replace('function ', '').strip()
                symbols.append(Symbol(name, 'function', filepath, i, line))
            elif line.startswith('class '):
                name = line.split(' ')[1].split(' ')[0].strip()
                symbols.append(Symbol(name, 'class', filepath, i, line))
            elif 'import ' in line:
                imports.append(line)
            elif 'export ' in line:
                exports.append(line)
        
        return {'symbols': symbols, 'imports': imports, 'exports': exports, 'references': references}
    
    def _parse_rust_file(self, filepath: str, content: str) -> Dict:
        """Basic Rust parsing."""
        symbols = []
        imports = []
        exports = []
        references = []
        
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            line = line.strip()
            
            if line.startswith('pub fn ') or line.startswith('fn '):
                # Handle both public and private functions
                fn_part = line.replace('pub fn ', '').replace('fn ', '')
                if '(' in fn_part:
                    name = fn_part.split('(')[0].strip()
                    symbols.append(Symbol(name, 'function', filepath, i, line))
            elif line.startswith('pub struct ') or line.startswith('struct '):
                # Handle both public and private structs
                struct_part = line.replace('pub struct ', '').replace('struct ', '')
                name = struct_part.split(' ')[0].split('{')[0].strip()
                symbols.append(Symbol(name, 'struct', filepath, i, line))
            elif line.startswith('use '):
                imports.append(line)
            elif line.startswith('pub '):
                exports.append(line)
        
        return {'symbols': symbols, 'imports': imports, 'exports': exports, 'references': references}
    
    def _analyze_python_dependencies(self, content: str) -> Dict:
        """Analyze Python dependencies."""
        internal_deps = []
        external_deps = []
        
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if self._is_internal_module(alias.name):
                                internal_deps.append(alias.name)
                            else:
                                external_deps.append(alias.name)
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        if self._is_internal_module(node.module):
                            internal_deps.append(node.module)
                        else:
                            external_deps.append(node.module)
        except SyntaxError:
            pass
        
        return {'internal_deps': internal_deps, 'external_deps': external_deps}
    
    def _analyze_javascript_dependencies(self, content: str) -> Dict:
        """Analyze JavaScript dependencies."""
        internal_deps = []
        external_deps = []
        
        lines = content.splitlines()
        for line in lines:
            line = line.strip()
            if 'import ' in line and 'from ' in line:
                parts = line.split('from ')
                if len(parts) > 1:
                    module = parts[1].strip().strip('\'"')
                    if module.startswith('.'):
                        internal_deps.append(module)
                    else:
                        external_deps.append(module)
        
        return {'internal_deps': internal_deps, 'external_deps': external_deps}
    
    def _analyze_rust_dependencies(self, content: str) -> Dict:
        """Analyze Rust dependencies."""
        internal_deps = []
        external_deps = []
        
        lines = content.splitlines()
        for line in lines:
            line = line.strip()
            if line.startswith('use '):
                module = line.replace('use ', '').split('::')[0].strip()
                if module.startswith('crate') or module.startswith('super') or module.startswith('self'):
                    internal_deps.append(module)
                else:
                    external_deps.append(module)
        
        return {'internal_deps': internal_deps, 'external_deps': external_deps}
    
    def _is_internal_module(self, module_name: str) -> bool:
        """Check if a module is internal to the project."""
        # Simple heuristic: check if module exists as file in project
        possible_paths = [
            self.root_path / f"{module_name}.py",
            self.root_path / module_name / "__init__.py"
        ]
        return any(path.exists() for path in possible_paths)
    
    def _detect_language(self, filepath: str) -> str:
        """Detect programming language from file extension."""
        ext = Path(filepath).suffix.lower()
        language_map = {
            '.py': 'python',
            '.js': 'javascript', 
            '.ts': 'typescript',
            '.rs': 'rust',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.go': 'go',
            '.rb': 'ruby',
            '.php': 'php'
        }
        return language_map.get(ext, 'unknown')
    
    def build_codebase_index(self, force_refresh: bool = False) -> Dict:
        """Build comprehensive index of the codebase."""
        print("Building enhanced codebase index...")
        
        # Get all source files
        patterns = ["**/*.py", "**/*.js", "**/*.ts", "**/*.rs", "**/*.java", "**/*.cpp", "**/*.c", "**/*.go"]
        all_files = []
        for pattern in patterns:
            all_files.extend(self.glob_files(pattern))
        
        # Process files
        total_symbols = 0
        processed_files = 0
        
        for filepath in all_files:
            try:
                file_info = self.get_file_context(filepath)
                if 'symbols' in file_info:
                    self.file_cache[filepath] = file_info
                    total_symbols += len(file_info['symbols'])
                    processed_files += 1
            except Exception as e:
                print(f"Error processing {filepath}: {e}")
        
        index_summary = {
            'total_files': len(all_files),
            'processed_files': processed_files,
            'total_symbols': total_symbols,
            'languages': list(set(self._detect_language(f) for f in all_files))
        }
        
        print(f"Enhanced index complete: {processed_files} files, {total_symbols} symbols")
        return index_summary

    def workspace_summary(self, max_files: int = 15) -> str:
        """Generate enhanced workspace summary with symbol information."""
        if not self.file_cache:
            self.build_codebase_index()
        
        files = self.glob_files("**/*")
        file_types = defaultdict(int)
        symbol_types = defaultdict(int)
        
        for file_path in files:
            if os.path.isfile(file_path):
                ext = os.path.splitext(file_path)[1]
                file_types[ext] += 1
        
        for file_info in self.file_cache.values():
            for symbol in file_info.get('symbols', []):
                symbol_types[symbol.kind] += 1
        
        summary = f"Enhanced Workspace Analysis: {self.root_path}\n"
        summary += f"Total files: {len(files)}\n"
        summary += f"Indexed files: {len(self.file_cache)}\n"
        summary += f"Total symbols: {sum(symbol_types.values())}\n\n"
        
        summary += "File types:\n"
        for ext, count in sorted(file_types.items()):
            if count > 0:
                summary += f"  {ext or 'no extension'}: {count}\n"
        
        summary += "\nSymbol types:\n"
        for sym_type, count in sorted(symbol_types.items()):
            summary += f"  {sym_type}: {count}\n"
        
        return summary

    def candidate_eoi_paths(self, limit: int = 20) -> List[str]:
        """Get enhanced candidate Entity of Interest paths based on symbol importance."""
        # Build index if not already done
        if not self.file_cache:
            self.build_codebase_index()
        
        candidates = []
        
        # Important file patterns (like before)
        important_patterns = [
            "**/README.md", "**/main.py", "**/lib.rs", "**/mod.rs",
            "**/index.js", "**/index.ts", "**/__init__.py",
            "**/package.json", "**/Cargo.toml", "**/pyproject.toml"
        ]
        
        for pattern in important_patterns:
            matches = self.glob_files(pattern)
            candidates.extend(matches)
        
        # Add files with many symbols (high-value files)
        symbol_counts = {}
        for file_path, file_info in self.file_cache.items():
            symbol_count = len(file_info.get('symbols', []))
            if symbol_count > 5:  # Files with many symbols are likely important
                symbol_counts[file_path] = symbol_count
        
        # Sort by symbol count and add top files
        top_symbol_files = sorted(symbol_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        candidates.extend([f[0] for f in top_symbol_files])
        
        return list(set(candidates))[:limit]

    def build_dependency_graph(self) -> Dict:
        """Build a dependency graph using NetworkX (if available)."""
        if not NETWORKX_AVAILABLE:
            return {"error": "NetworkX not available for dependency graph analysis"}
        
        G = nx.DiGraph()
        
        # Add nodes for all files
        for file_path in self.file_cache.keys():
            G.add_node(file_path)
        
        # Add edges for dependencies
        for file_path, file_info in self.file_cache.items():
            for dep in file_info.get('internal_deps', []):
                dep_path = self._resolve_dependency_path(dep, file_path)
                if dep_path and dep_path in self.file_cache:
                    G.add_edge(file_path, dep_path)
        
        # Calculate centrality measures
        centrality = {}
        try:
            centrality['betweenness'] = nx.betweenness_centrality(G)
            centrality['pagerank'] = nx.pagerank(G)
            centrality['in_degree'] = dict(G.in_degree())
            centrality['out_degree'] = dict(G.out_degree())
        except:
            centrality = {"error": "Could not calculate centrality measures"}
        
        return {
            'nodes': G.number_of_nodes(),
            'edges': G.number_of_edges(),
            'centrality': centrality
        }
    
    def _resolve_dependency_path(self, dependency: str, from_file: str) -> Optional[str]:
        """Resolve a dependency string to an actual file path."""
        # This is a simplified version - could be much more sophisticated
        base_dir = os.path.dirname(from_file)
        
        # Try common patterns
        candidates = [
            os.path.join(base_dir, f"{dependency}.py"),
            os.path.join(base_dir, dependency, "__init__.py"),
            os.path.join(self.root_path, f"{dependency}.py"),
            os.path.join(self.root_path, dependency, "__init__.py")
        ]
        
        for candidate in candidates:
            if os.path.exists(candidate):
                return candidate
        
        return None
