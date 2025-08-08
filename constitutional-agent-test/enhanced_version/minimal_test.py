#!/usr/bin/env python3
"""
Minimal test to verify the agent works with real LLM
Uses cheapest model and simplest task to minimize cost
"""

import os
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from agent_enhanced import EnhancedConstitutionalAgent

def minimal_llm_test():
    """
    Minimal test that:
    1. Analyzes existing code (no generation)
    2. Uses minimal tokens
    3. Exits quickly
    """
    
    print("\n" + "="*60)
    print("MINIMAL LLM TEST - Low Cost")
    print("="*60)
    
    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("\n❌ No API key found")
        print("Set: export ANTHROPIC_API_KEY=your_key")
        return False
    
    try:
        # Create agent
        workspace = Path.cwd().parent.parent
        agent = EnhancedConstitutionalAgent(
            workspace_root=str(workspace),
            data_dir=str(Path.cwd().parent / "data")
        )
        
        # MINIMAL TASK - Just analyze, don't generate
        task = "List the main components in server/world/systems/"
        
        print(f"\nTask: {task}")
        print("(This will only analyze, not generate code)\n")
        
        # Override to use cheaper model
        if agent.llm:
            # Use Claude 3 Haiku (10x cheaper than Opus)
            agent.llm.model = "claude-3-haiku-20240307"
            print("Using Claude 3 Haiku (cheaper model)")
        
        # Just run the planning phase, not full execution
        agent.switch_mode("constitutional")
        plan = agent._plan_implementation(task, None)
        
        print("\nPlan created:")
        for i, step in enumerate(plan, 1):
            print(f"  {i}. {step.get('description', 'Unknown')}")
        
        print("\n✅ Test successful - LLM connection works")
        print("No code was generated (to save tokens)")
        
        # Estimate cost
        print("\nEstimated cost: < $0.01")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run minimal test"""
    print("\nThis test will:")
    print("1. Use the CHEAPEST model (Haiku)")
    print("2. Only ANALYZE code (no generation)")
    print("3. Exit after planning (no execution)")
    print("4. Cost < $0.01")
    
    response = input("\nProceed? (y/n): ")
    if response.lower() != 'y':
        print("Test cancelled")
        return 1
    
    success = minimal_llm_test()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
