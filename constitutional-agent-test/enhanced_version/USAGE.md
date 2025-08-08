# Constitutional Agent - Usage Guide

## Overview

This is a minimal implementation of a Constitutional Agent that can:
- Interact with real codebases (read/write/search files)
- Execute commands (cargo build/test/check)
- Generate architecture and code using LLM (when API key available)
- Maintain constitutional features (EoI navigation, two-tier thinking, reflections)

## Setup

1. **Install Python dependencies:**
```bash
cd constitutional-agent-test
python3 -m venv venv
source venv/bin/activate
pip install anthropic pyyaml tiktoken
```

2. **Set API key (optional, for LLM features):**
```bash
export ANTHROPIC_API_KEY=your_key_here
```

## Quick Test

Test the agent without making changes:
```bash
python test_enhanced_agent.py
```

This will:
- Test file operations and codebase analysis
- Test command execution
- Test EoI navigation and mode switching
- If API key is set, test LLM generation (analysis only, no file changes)

## Using the Agent

### Basic Usage (Python)

```python
from agent_enhanced import EnhancedConstitutionalAgent

# Create agent pointing at Voxelize root
agent = EnhancedConstitutionalAgent(
    workspace_root="/workspaces/vox2",
    data_dir="data"
)

# Execute a task
results = agent.execute_task(
    task="Add XP tracking to player progression",
    requirements="Must integrate with existing ECS"
)
```

### Without LLM (Analysis Only)

Even without an API key, the agent can:

```python
# Analyze codebase structure
structure = agent.analyze_codebase()
print(f"Found {len(structure['rust_files'])} Rust files")

# Search for patterns
matches = agent.search_code("Component")
for match in matches[:5]:
    print(f"{match.file_path}:{match.line_number} - {match.line_content}")

# Run commands
result = agent.run_command("cargo check")
if result["success"]:
    print("Code compiles!")
```

### With LLM (Full Capabilities)

With an API key set, the agent can:
- Generate architecture documents
- Generate Rust code
- Review implementations
- Iterate on compilation errors

## Architecture

```
agent_enhanced.py
    ├── Inherits from ConstitutionalAgent (base)
    ├── Uses FileTools (file operations)
    ├── Uses CommandTools (cargo commands)
    ├── Uses CodebaseTools (analysis)
    └── Uses LLMClient (when available)
```

## Execution Flow

1. **Planning Phase** (Constitutional Mode)
   - Analyze codebase structure
   - Find relevant files
   - Generate architecture (with LLM) or manual plan

2. **Implementation Phase** (Execution Mode)
   - Navigate to appropriate EoI
   - Generate/modify code
   - Track results

3. **Testing Phase**
   - Run cargo check
   - Run cargo test
   - Detect error patterns

4. **Review Phase** (Constitutional Mode)
   - Reflect on results
   - Suggest EoI shifts if needed
   - Capture learnings

## Key Features

### Tool Integration
- **FileTools**: Read, write, edit, search files
- **CommandTools**: Run cargo and shell commands
- **CodebaseTools**: Analyze project structure, find relevant files

### Constitutional Features
- **EoI Navigation**: Focus on different entities (system, component, architecture)
- **Mode Switching**: Constitutional (planning/reflection) vs Execution (implementation)
- **Reflection Protocol**: Capture insights and learnings

### LLM Integration (Optional)
- **Architecture Generation**: Create detailed designs
- **Code Generation**: Generate Rust implementations
- **Code Review**: Analyze generated code

## Limitations

Current implementation is minimal and has limitations:
- No state persistence between runs
- Simple error recovery (no sophisticated retry logic)
- Basic context selection (could be smarter about relevant files)
- No multi-agent coordination
- No advanced task tree navigation

## Next Steps

To extend this agent:

1. **Add persistence**: Save state between runs
2. **Improve context selection**: Smarter relevant file detection
3. **Add iterative refinement**: Multiple attempts with error analysis
4. **Enhance task management**: Full task tree support
5. **Add multi-agent support**: Reviewer/implementer pattern

## Comparison to Production Systems

This is much simpler than Claude Code or Open SWE, but it:
- ✅ Works with real files and commands
- ✅ Integrates with LLM for generation
- ✅ Maintains constitutional architecture concepts
- ✅ Can be extended incrementally

What it lacks:
- ❌ Sophisticated state management
- ❌ Advanced error recovery
- ❌ Parallel execution
- ❌ Production-grade robustness

This is intentionally minimal to:
1. Test constitutional concepts quickly
2. Avoid framework complexity
3. Allow rapid iteration
4. Provide clear upgrade path
