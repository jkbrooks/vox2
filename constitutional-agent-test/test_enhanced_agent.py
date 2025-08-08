#!/usr/bin/env python3
"""
Test script for the enhanced constitutional agent
Tests both with and without LLM capabilities
"""

import os
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from agent_enhanced import EnhancedConstitutionalAgent

def test_without_llm():
    """Test agent capabilities without LLM"""
    print("\n" + "="*60)
    print("Testing WITHOUT LLM (analysis only)")
    print("="*60)
    
    # Temporarily hide API key
    api_key = os.environ.pop("ANTHROPIC_API_KEY", None)
    
    try:
        # Create agent (should work without API key)
        workspace = Path.cwd().parent
        agent = EnhancedConstitutionalAgent(
            workspace_root=str(workspace),
            data_dir="data"
        )
        
        # Test basic capabilities
        print("\n1. Analyzing codebase structure...")
        structure = agent.analyze_codebase()
        print(f"   ✓ Found {len(structure['rust_files'])} Rust files")
        print(f"   ✓ Found {len(structure['directories'])} directories")
        
        print("\n2. Searching for 'Component' in code...")
        matches = agent.search_code("Component")
        print(f"   ✓ Found {len(matches)} matches")
        if matches:
            print(f"   First match: {matches[0].file_path}:{matches[0].line_number}")
        
        print("\n3. Testing command execution...")
        result = agent.run_command("cargo --version")
        if result["success"]:
            print(f"   ✓ Cargo version: {result['stdout'].strip()}")
        else:
            print(f"   ✗ Command failed: {result['stderr']}")
        
        print("\n4. Testing EoI navigation...")
        agent.navigate_eoi("system", "Testing navigation")
        print(f"   ✓ Current EoI: {agent.current_eoi}")
        
        print("\n5. Testing mode switching...")
        agent.switch_mode("constitutional")
        print(f"   ✓ Current mode: {agent.mode}")
        
        print("\n✅ All basic tests passed!")
        
    finally:
        # Restore API key if it existed
        if api_key:
            os.environ["ANTHROPIC_API_KEY"] = api_key

def test_with_llm():
    """Test agent with LLM capabilities"""
    print("\n" + "="*60)
    print("Testing WITH LLM (full capabilities)")
    print("="*60)
    
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠️  No API key found. Skipping LLM tests.")
        print("   Set ANTHROPIC_API_KEY environment variable to enable.")
        return
    
    # Create agent with LLM
    workspace = Path.cwd().parent
    agent = EnhancedConstitutionalAgent(
        workspace_root=str(workspace),
        data_dir="data"
    )
    
    # Simple task that won't break anything
    task = "Analyze the player progression system architecture"
    
    print(f"\nExecuting task: {task}")
    results = agent.execute_task(task)
    
    print("\nResults:")
    print(f"  Plan steps: {len(results.get('plan', []))}")
    print(f"  Implementation results: {len(results.get('implementation', []))}")
    print(f"  Compilation: {results.get('tests', {}).get('compiles', 'unknown')}")
    print(f"  Success: {results.get('review', {}).get('success', False)}")
    
    if results.get('reflections'):
        print("\nReflections:")
        for r in results['reflections']:
            print(f"  - {r.get('insight', r)[:80]}...")

def main():
    """Run all tests"""
    print("\n" + "="*70)
    print(" ENHANCED CONSTITUTIONAL AGENT TEST SUITE")
    print("="*70)
    
    # Check if we're in the right place
    workspace = Path.cwd().parent
    if not (workspace / "Cargo.toml").exists():
        print("\n❌ Error: Must run from constitutional-agent-test directory")
        print(f"   Current: {Path.cwd()}")
        print(f"   Expected: vox2/constitutional-agent-test/")
        return 1
    
    print(f"\n📁 Workspace: {workspace}")
    print(f"   Cargo.toml: {'✓' if (workspace / 'Cargo.toml').exists() else '✗'}")
    
    # Run tests
    try:
        test_without_llm()
        test_with_llm()
        
        print("\n" + "="*70)
        print(" ✅ ALL TESTS COMPLETE")
        print("="*70)
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
