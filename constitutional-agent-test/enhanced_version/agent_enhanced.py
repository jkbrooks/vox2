"""
Enhanced Constitutional Agent with Tool Integration
Extends the base agent with real codebase interaction capabilities
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

# Import base agent and new tools
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "original_version"))
from agent import ConstitutionalAgent

# Import tools from current directory
from tools import FileTools, CommandTools, CodebaseTools
from llm_client import LLMClient

class ExecutionState(Enum):
    """States for the execution loop"""
    PLANNING = "planning"
    IMPLEMENTING = "implementing"
    TESTING = "testing"
    REVIEWING = "reviewing"
    COMPLETE = "complete"

class EnhancedConstitutionalAgent(ConstitutionalAgent):
    """Constitutional Agent with real tool capabilities"""
    
    def __init__(self, workspace_root: str = ".", **kwargs):
        # Initialize base agent
        super().__init__(**kwargs)
        
        # Initialize tools
        self.workspace_root = Path(workspace_root).resolve()
        self.file_tools = FileTools(workspace_root)
        self.command_tools = CommandTools(workspace_root)
        self.codebase_tools = CodebaseTools(workspace_root)
        
        # Initialize LLM (will be None if no API key)
        try:
            self.llm = LLMClient()
        except ValueError:
            print("Warning: No ANTHROPIC_API_KEY found. LLM features disabled.")
            self.llm = None
        
        # Execution state
        self.state = ExecutionState.PLANNING
        self.current_plan = []
        self.implementation_results = []
        
    def execute_task(self, task_description: str, requirements: Optional[str] = None) -> Dict:
        """Execute a complete development task"""
        
        print(f"\n{'='*60}")
        print(f"Constitutional Agent: Executing Task")
        print(f"{'='*60}")
        print(f"Task: {task_description}")
        
        # Start in constitutional mode for planning
        self.switch_mode("constitutional")
        self.state = ExecutionState.PLANNING
        
        results = {
            "task": task_description,
            "started": datetime.now().isoformat(),
            "steps": []
        }
        
        # Main execution loop
        while self.state != ExecutionState.COMPLETE:
            
            if self.state == ExecutionState.PLANNING:
                plan = self._plan_implementation(task_description, requirements)
                results["plan"] = plan
                self.state = ExecutionState.IMPLEMENTING
                
            elif self.state == ExecutionState.IMPLEMENTING:
                impl_results = self._implement_plan()
                results["implementation"] = impl_results
                self.state = ExecutionState.TESTING
                
            elif self.state == ExecutionState.TESTING:
                test_results = self._test_implementation()
                results["tests"] = test_results
                self.state = ExecutionState.REVIEWING
                
            elif self.state == ExecutionState.REVIEWING:
                review = self._review_results(results)
                results["review"] = review
                self.state = ExecutionState.COMPLETE
        
        results["completed"] = datetime.now().isoformat()
        results["reflections"] = self.reflection_log[-5:]  # Last 5 reflections
        
        return results
    
    def _plan_implementation(self, task: str, requirements: Optional[str]) -> List[Dict]:
        """Plan the implementation approach"""
        
        print("\n📋 Planning Phase")
        print("-" * 40)
        
        # Analyze codebase
        structure = self.codebase_tools.analyze_structure()
        print(f"Found {len(structure['rust_files'])} Rust files")
        print(f"Found {len(structure['test_files'])} test files")
        
        # Find relevant files
        relevant_files = self.codebase_tools.find_relevant_files(task)
        print(f"Identified {len(relevant_files)} relevant files")
        
        # Load context from relevant files
        context = {}
        for file_path in relevant_files[:5]:  # Limit for token budget
            try:
                context[file_path] = self.file_tools.read_file(file_path)
                print(f"  ✓ Loaded {file_path}")
            except:
                print(f"  ⚠ Could not load {file_path}")
        
        # Generate plan (with or without LLM)
        if self.llm:
            print("\nGenerating implementation plan with LLM...")
            architecture = self.llm.generate_architecture(task, requirements or "", context)
            
            # Create structured plan from architecture
            plan = [
                {
                    "step": "analyze",
                    "description": "Analyze existing codebase structure",
                    "completed": True
                },
                {
                    "step": "design",
                    "description": "Design component architecture",
                    "architecture": architecture,
                    "completed": True
                },
                {
                    "step": "implement",
                    "description": "Implement core components",
                    "files": relevant_files[:3] if relevant_files else ["server/world/systems/progression.rs"]
                },
                {
                    "step": "test",
                    "description": "Write and run tests"
                }
            ]
        else:
            print("\nCreating manual plan (no LLM available)...")
            plan = [
                {
                    "step": "analyze",
                    "description": "Analyze codebase",
                    "completed": True
                },
                {
                    "step": "implement",
                    "description": "Create implementation",
                    "files": relevant_files[:3] if relevant_files else []
                }
            ]
        
        self.current_plan = plan
        
        # Capture insight
        self.capture_reflection(f"Created {len(plan)}-step plan for: {task}")
        
        return plan
    
    def _implement_plan(self) -> List[Dict]:
        """Implement based on the plan"""
        
        print("\n🔨 Implementation Phase")
        print("-" * 40)
        
        # Switch to execution mode
        self.switch_mode("execution")
        
        results = []
        
        for step in self.current_plan:
            if step.get("completed"):
                continue
                
            print(f"\nImplementing: {step['description']}")
            
            if step["step"] == "implement" and "files" in step:
                for file_path in step["files"]:
                    
                    # Navigate to appropriate EoI
                    if "component" in file_path.lower():
                        self.navigate_eoi("component", f"Implementing {file_path}")
                    elif "system" in file_path.lower():
                        self.navigate_eoi("system", f"Implementing {file_path}")
                    
                    if self.llm:
                        # Generate code with LLM
                        print(f"  Generating code for {file_path}...")
                        
                        # Check if file exists
                        existing_code = None
                        try:
                            existing_code = self.file_tools.read_file(file_path)
                        except:
                            pass
                        
                        code = self.llm.generate_code(
                            task=step["description"],
                            architecture=step.get("architecture", ""),
                            file_path=file_path,
                            context=existing_code
                        )
                        
                        # Write the code
                        try:
                            self.file_tools.write_file(file_path, code)
                            results.append({
                                "file": file_path,
                                "action": "modified" if existing_code else "created",
                                "success": True
                            })
                            print(f"  ✓ {'Modified' if existing_code else 'Created'} {file_path}")
                        except Exception as e:
                            results.append({
                                "file": file_path,
                                "action": "failed",
                                "error": str(e)
                            })
                            print(f"  ✗ Failed: {e}")
                    else:
                        # Without LLM, just report what would be done
                        results.append({
                            "file": file_path,
                            "action": "would_implement",
                            "note": "LLM not available"
                        })
                        print(f"  ⚠ Would implement {file_path} (no LLM)")
        
        return results
    
    def _test_implementation(self) -> Dict:
        """Test the implementation"""
        
        print("\n🧪 Testing Phase")
        print("-" * 40)
        
        results = {}
        
        # Check if project compiles
        print("Running cargo check...")
        check_result = self.command_tools.run_cargo_check()
        results["compiles"] = check_result.success
        
        if check_result.success:
            print("  ✓ Code compiles")
        else:
            print("  ✗ Compilation errors:")
            print(f"    {check_result.stderr[:200]}")
            
            # Detect error pattern for EoI shift
            self.detect_eoi_shift_trigger("compilation_error")
        
        # Run tests
        print("\nRunning cargo test...")
        test_result = self.command_tools.run_cargo_test()
        results["tests_pass"] = test_result.success
        
        if test_result.success:
            print("  ✓ Tests pass")
        else:
            print("  ⚠ Test failures (may be expected for new code)")
        
        results["stdout"] = test_result.stdout[:500]
        results["stderr"] = test_result.stderr[:500]
        
        return results
    
    def _review_results(self, results: Dict) -> Dict:
        """Review and reflect on results"""
        
        print("\n📝 Review Phase")
        print("-" * 40)
        
        # Switch to constitutional mode for reflection
        self.switch_mode("constitutional")
        
        review = {
            "success": results.get("tests", {}).get("compiles", False),
            "files_changed": len(results.get("implementation", [])),
            "insights": []
        }
        
        # Generate insights
        if review["success"]:
            insight = "Successfully implemented task with compilation passing"
        else:
            insight = "Implementation incomplete - compilation or tests failing"
        
        self.capture_reflection(insight)
        review["insights"].append(insight)
        
        # Check for patterns requiring EoI shift
        if not review["success"]:
            suggestions = self.get_eoi_navigation_suggestions()
            if suggestions:
                review["eoi_suggestions"] = suggestions
                print(f"  Suggested EoI shifts: {', '.join(suggestions)}")
        
        print(f"\n✓ Review complete: {'Success' if review['success'] else 'Needs work'}")
        
        return review
    
    def analyze_codebase(self) -> Dict:
        """Analyze the current codebase structure"""
        return self.codebase_tools.analyze_structure()
    
    def search_code(self, pattern: str) -> List:
        """Search for pattern in codebase"""
        return self.file_tools.search_files(pattern)
    
    def run_command(self, command: str) -> Dict:
        """Run arbitrary command"""
        result = self.command_tools.run_command(command)
        return {
            "success": result.success,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.return_code
        }

def main():
    """Test the enhanced agent"""
    import sys
    
    # Check workspace
    workspace = Path.cwd().parent  # Go up from constitutional-agent-test
    if not (workspace / "Cargo.toml").exists():
        print("Error: Not in Voxelize workspace")
        return 1
    
    # Create agent
    agent = EnhancedConstitutionalAgent(
        workspace_root=str(workspace),
        data_dir="data"
    )
    
    # Simple task
    task = "Add a new component for tracking player XP"
    
    # Execute
    results = agent.execute_task(task)
    
    # Print summary
    print("\n" + "="*60)
    print("Execution Summary")
    print("="*60)
    print(json.dumps(results, indent=2))
    
    return 0 if results.get("review", {}).get("success") else 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
