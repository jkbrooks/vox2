# Constitutional Agent Test

This repository contains two versions of the Constitutional Agent implementation.

## Directory Structure

```
constitutional-agent-test/
├── enhanced_version/     # ACTIVE - Enhanced agent with tool integration
├── original_version/     # DEPRECATED - Original implementation (for reference)
├── data/                # Shared data files (used by both versions)
├── prompts/             # Shared prompts (used by both versions)
├── analysis/            # Metrics and analysis
├── logs/                # Session logs
└── venv/                # Python virtual environment
```

## Active Version: Enhanced Agent

**Location:** `enhanced_version/`

The enhanced version adds real codebase interaction capabilities:
- File operations (read/write/search)
- Command execution (cargo build/test/check)
- LLM integration for code generation
- Maintains all constitutional features

**Key Files:**
- `agent_enhanced.py` - Main enhanced agent
- `tools.py` - File and command tools
- `llm_client.py` - LLM integration
- `test_enhanced_agent.py` - Test suite
- `USAGE.md` - Detailed usage guide
- `IMPLEMENTATION_PLAN.md` - Architecture decisions

**To use:** See `enhanced_version/USAGE.md`

## Original Version (Deprecated)

**Location:** `original_version/`

The original implementation focused on:
- Constitutional architecture concepts
- EoI (Entity of Interest) navigation
- Dynamic context injection
- Two-tier thinking modes

This version is kept for reference and comparison but is not actively developed.

**Key Files:**
- `agent.py` - Original base agent
- `context_manager.py` - Context injection system
- Tests and documentation

## Shared Resources

**Location:** Root directory

- `data/` - Sample data (entities, stakeholders, viewpoints)
- `prompts/` - Constitutional system prompt
- `venv/` - Python environment

## Quick Start

```bash
# Setup
cd constitutional-agent-test
source venv/bin/activate

# Test enhanced version
cd enhanced_version
python test_enhanced_agent.py

# With LLM (requires API key)
export ANTHROPIC_API_KEY=your_key_here
python test_enhanced_agent.py
```

## Migration Status

We are transitioning from the original to the enhanced version. The enhanced version:
- ✅ Preserves all constitutional features
- ✅ Adds real tool capabilities
- ✅ Works with actual codebases
- ✅ Integrates with LLM for generation

The original version will be removed once the enhanced version is fully validated.
