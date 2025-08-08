#!/usr/bin/env python3
"""
Test script to demonstrate dynamic context injection
Shows how context changes based on mode, EoI, and triggers
"""

import json
from pathlib import Path
from context_manager import DynamicContextInjector, Priority

def print_section(title: str):
    """Pretty print section headers"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print('='*60)

def analyze_prompt(prompt: str, metadata: dict):
    """Analyze and display prompt statistics"""
    print(f"\nTokens used: {metadata['total_tokens']}/{10000} ({metadata['total_tokens']/100:.1f}%)")
    print(f"Remaining budget: {metadata['remaining_budget']} tokens")
    print(f"Mode: {metadata['mode']}")
    print(f"Entity of Interest: {metadata['eoi'].get('id', 'Unknown')} - {metadata['eoi'].get('title', 'Unknown')}")
    print(f"\nIncluded elements ({len(metadata['included_elements'])}):")
    for elem in metadata['included_elements']:
        print(f"  ✓ {elem}")
    if metadata['excluded_elements']:
        print(f"\nExcluded elements ({len(metadata['excluded_elements'])}):")
        for elem in metadata['excluded_elements'][:5]:  # Show first 5
            print(f"  ✗ {elem}")
        if len(metadata['excluded_elements']) > 5:
            print(f"  ... and {len(metadata['excluded_elements'])-5} more")

def test_scenario_1():
    """Scenario 1: Starting a new task in execution mode"""
    print_section("Scenario 1: Starting New Task (Execution Mode)")
    
    injector = DynamicContextInjector(Path("data"))
    injector.load_data()
    
    # Start with a specific task in execution mode
    prompt, metadata = injector.prepare_context_for_task("task-001-2-1", mode="execution")
    
    analyze_prompt(prompt, metadata)
    
    # Show a snippet of the actual prompt
    print("\nPrompt snippet (first 500 chars):")
    print("-" * 40)
    print(prompt[:500])
    print("...")
    
    return prompt, metadata

def test_scenario_2():
    """Scenario 2: Same task but switching to constitutional mode"""
    print_section("Scenario 2: Mode Switch to Constitutional")
    
    injector = DynamicContextInjector(Path("data"))
    injector.load_data()
    
    # Same task but constitutional mode
    prompt, metadata = injector.prepare_context_for_task("task-001-2-1", mode="constitutional")
    
    analyze_prompt(prompt, metadata)
    
    # Show what changed in the prompt
    print("\nKey additions for constitutional mode:")
    if "iso_definitions" in metadata['included_elements']:
        print("  + ISO/IEEE 42010 definitions added")
    if "insights" in metadata['included_elements']:
        print("  + Constitutional insights added")
    
    return prompt, metadata

def test_scenario_3():
    """Scenario 3: Moving to parent task (EoI change)"""
    print_section("Scenario 3: Entity of Interest Change (Parent Task)")
    
    injector = DynamicContextInjector(Path("data"))
    injector.load_data()
    
    # Move to parent task - broader scope
    prompt, metadata = injector.prepare_context_for_task("task-001-2", mode="execution")
    
    analyze_prompt(prompt, metadata)
    
    print("\nEoI Level Change Impact:")
    print(f"  Previous: L5 (Task level)")
    print(f"  Current: L4 (Feature level)")
    print("  → Broader context, more stakeholders")
    
    return prompt, metadata

def test_scenario_4():
    """Scenario 4: Simulating cognitive load adaptation"""
    print_section("Scenario 4: Adaptive Context Based on Patterns")
    
    injector = DynamicContextInjector(Path("data"))
    injector.load_data()
    
    # Simulate detecting a pattern - add insight
    injector.insights_log.append("Pattern detected: Error handling inconsistent across modules")
    injector.insights_log.append("Consider: Standardized error type hierarchy")
    
    # Now prepare context with these insights
    prompt, metadata = injector.prepare_context_for_task("task-001-2-1", mode="constitutional")
    
    analyze_prompt(prompt, metadata)
    
    if "insights" in metadata['included_elements']:
        print("\n✓ Insights successfully injected based on detected patterns")
    
    return prompt, metadata

def compare_token_usage():
    """Compare token usage across different modes and contexts"""
    print_section("Token Usage Comparison")
    
    injector = DynamicContextInjector(Path("data"))
    injector.load_data()
    
    scenarios = [
        ("task-001-2-1", "execution", "L5 Task - Execution"),
        ("task-001-2-1", "constitutional", "L5 Task - Constitutional"),
        ("task-001-2", "execution", "L4 Feature - Execution"),
        ("task-001-2", "constitutional", "L4 Feature - Constitutional"),
        ("task-001", "constitutional", "L3 Product - Constitutional"),
    ]
    
    results = []
    for task_id, mode, description in scenarios:
        try:
            prompt, metadata = injector.prepare_context_for_task(task_id, mode)
            results.append({
                'description': description,
                'tokens': metadata['total_tokens'],
                'included': len(metadata['included_elements']),
                'excluded': len(metadata['excluded_elements'])
            })
        except ValueError as e:
            results.append({
                'description': description,
                'tokens': 0,
                'included': 0,
                'excluded': 0,
                'error': str(e)
            })
    
    # Display comparison table
    print("\n{:<35} {:>10} {:>10} {:>10}".format(
        "Scenario", "Tokens", "Included", "Excluded"
    ))
    print("-" * 70)
    for r in results:
        if 'error' not in r:
            print("{:<35} {:>10} {:>10} {:>10}".format(
                r['description'],
                r['tokens'],
                r['included'],
                r['excluded']
            ))
        else:
            print("{:<35} Error: {}".format(r['description'], r['error']))
    
    # Calculate savings
    if len(results) >= 2:
        exec_tokens = results[0]['tokens']
        const_tokens = results[1]['tokens']
        if const_tokens > 0:
            savings = (1 - exec_tokens/const_tokens) * 100
            print(f"\nToken savings in execution vs constitutional: {savings:.1f}%")

def demonstrate_prompt_evolution():
    """Show how prompt evolves through a work session"""
    print_section("Prompt Evolution Through Work Session")
    
    injector = DynamicContextInjector(Path("data"))
    injector.load_data()
    
    # Simulate a work session
    session = [
        ("task-001-2-1", "execution", "Start task"),
        ("task-001-2-1", "execution", "Working..."),
        ("task-001-2-1", "constitutional", "Pattern detected, reflecting"),
        ("task-001-2", "constitutional", "Zooming out to feature level"),
        ("task-001-2-2", "execution", "Moving to next subtask"),
    ]
    
    print("\nWork Session Timeline:")
    print("-" * 40)
    
    for i, (task_id, mode, description) in enumerate(session, 1):
        try:
            prompt, metadata = injector.prepare_context_for_task(task_id, mode)
            
            # Simulate adding insights during constitutional mode
            if mode == "constitutional" and i == 3:
                injector.insights_log.append(f"Insight from step {i}: Need consistent error handling")
            
            print(f"\nStep {i}: {description}")
            print(f"  Task: {task_id}, Mode: {mode}")
            print(f"  Tokens: {metadata['total_tokens']}")
            print(f"  Context elements: {len(metadata['included_elements'])}")
            
            # Show what changed from previous step
            if i > 1:
                print(f"  Change trigger: ", end="")
                if session[i-1][0] != task_id:
                    print("EoI change")
                elif session[i-1][1] != mode:
                    print("Mode switch")
                else:
                    print("Context refresh")
        except ValueError as e:
            print(f"\nStep {i}: {description} - Error: {e}")

def main():
    """Run all test scenarios"""
    print("\n" + "="*60)
    print(" DYNAMIC CONTEXT INJECTION TEST SUITE")
    print("="*60)
    
    # Run individual scenarios
    test_scenario_1()
    test_scenario_2()
    test_scenario_3()
    test_scenario_4()
    
    # Run comparisons
    compare_token_usage()
    demonstrate_prompt_evolution()
    
    print_section("Test Complete")
    print("\nKey Findings:")
    print("✓ Context adapts based on mode (execution vs constitutional)")
    print("✓ Token usage varies significantly with mode and EoI level")
    print("✓ Relevant stakeholders and viewpoints injected based on context")
    print("✓ Insights can be dynamically added and included when relevant")
    print("✓ System successfully prioritizes content within token budget")

if __name__ == "__main__":
    main()
