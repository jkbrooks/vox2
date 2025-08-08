# Constitutional Agent Implementation Plan

## Current State
We have a constitutional agent with:
- EoI (Entity of Interest) navigation
- Dynamic context injection with token budgeting
- Two-tier thinking (constitutional/execution modes)
- ISO/IEEE 42010 integration
- Reflection protocol

## Critical Gap
The agent cannot interact with the actual codebase. It needs:
1. **File operations** - Read/write/edit actual files
2. **Command execution** - Run builds, tests, linters
3. **Iterative development** - Plan → Execute → Test → Fix cycle

## Proposed Solution: Minimal Tool Layer

Rather than adopting a full framework (Claude Code or Open SWE), we'll add a minimal tool layer to our existing constitutional agent. This preserves our unique features while adding essential capabilities.

## Implementation Approach

### Phase 1: Core Tools (Immediate)
Create a single `tools.py` module with:
```python
class FileTools:
    - read_file(path) -> str
    - write_file(path, content)
    - edit_file(path, old, new)
    - search_files(pattern) -> List[Match]

class CommandTools:
    - run_command(cmd) -> Result
    - run_cargo_test() -> TestResult
    - run_cargo_build() -> BuildResult

class CodebaseTools:
    - analyze_structure() -> Structure
    - find_relevant_files(task) -> List[Path]
```

### Phase 2: LLM Integration
Create `llm_client.py` with:
```python
class LLMClient:
    - generate_architecture(requirements, context) -> str
    - generate_code(task, architecture, context) -> str
    - review_code(code, requirements) -> Review
```

### Phase 3: Agent Enhancement
Update `agent.py` to:
```python
class ConstitutionalAgentWithTools:
    - Inherits from ConstitutionalAgent
    - Adds tool usage
    - Implements iterative loop
    - Maintains all constitutional features
```

## Why This Approach?

1. **Preserves our unique features** - EoI navigation, constitutional architecture
2. **Minimal complexity** - No framework overhead
3. **Fast iteration** - Can test immediately
4. **Clear upgrade path** - Can adopt framework later if needed

## Next Steps

1. Create the tool layer (1 file, ~300 lines)
2. Add LLM client (1 file, ~200 lines)  
3. Enhance agent (update existing file)
4. Test on real Voxelize tasks

This gives us a working system in ~500 lines of new code, versus thousands for a framework adoption.
