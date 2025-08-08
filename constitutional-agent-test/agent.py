import os
import json
import yaml
import subprocess
import re
from pathlib import Path
from typing import Dict, List, Optional, Any

class ConstitutionalAgent:
    def __init__(self, 
                 prompt_path="prompts/constitutional_system_prompt.md",
                 data_dir="data"):
        self.data_dir = Path(data_dir)
        self.prompt_template = self.load_prompt_template(prompt_path)
        self.task_tree = self.load_task_tree()
        self.stakeholders = self.load_stakeholders()
        self.viewpoints = self.load_viewpoints()
        self.current_task_id = None
        self.mode = "execution"  # or "constitutional"
        self.reflection_log = []
        
    def load_prompt_template(self, path):
        """Loads the constitutional prompt template from the given path."""
        try:
            with open(path, 'r') as f:
                return f.read()
        except FileNotFoundError:
            return "Error: Prompt template not found."
    
    def load_task_tree(self):
        """Loads the task tree from YAML."""
        tree_path = self.data_dir / "sample_task_tree.yaml"
        try:
            with open(tree_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"Warning: Task tree not found at {tree_path}")
            return {}
    
    def load_stakeholders(self):
        """Loads stakeholder definitions from YAML."""
        stakeholder_path = self.data_dir / "stakeholders.yaml"
        try:
            with open(stakeholder_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"Warning: Stakeholders not found at {stakeholder_path}")
            return {}
    
    def load_viewpoints(self):
        """Loads viewpoint documents from the viewpoints directory."""
        viewpoints = {}
        viewpoint_dir = self.data_dir / "viewpoints"
        if viewpoint_dir.exists():
            for vp_file in viewpoint_dir.glob("*.md"):
                with open(vp_file, 'r') as f:
                    viewpoints[vp_file.stem] = f.read()
        return viewpoints
    
    def navigate_to_task(self, task_id: str):
        """Navigate to a specific task in the tree."""
        self.current_task_id = task_id
        task = self.find_task(task_id)
        if task:
            print(f"Navigated to task: {task.get('title', 'Unknown')}")
            return task
        else:
            print(f"Task {task_id} not found")
            return None
    
    def find_task(self, task_id: str, node: Dict = None) -> Optional[Dict]:
        """Recursively find a task by ID in the tree."""
        if node is None:
            node = self.task_tree.get('root', {})
        
        if node.get('id') == task_id:
            return node
        
        for child in node.get('children', []):
            result = self.find_task(task_id, child)
            if result:
                return result
        return None
    
    def get_local_context(self, task_id: str = None) -> Dict:
        """Get the local context around a task (parent, siblings, children)."""
        if task_id is None:
            task_id = self.current_task_id
        
        task = self.find_task(task_id)
        if not task:
            return {}
        
        context = {
            'current': task,
            'children': task.get('children', []),
            'dependencies': task.get('dependencies', []),
            'level': task.get('level', 'Unknown'),
            'entity_of_interest': task.get('entity_of_interest', 'Unknown')
        }
        
        # Find parent (simplified - in real implementation would track parent)
        context['parent'] = self._find_parent(task_id)
        
        return context
    
    def _find_parent(self, task_id: str, node: Dict = None) -> Optional[Dict]:
        """Find the parent of a task (simplified implementation)."""
        if node is None:
            node = self.task_tree.get('root', {})
        
        for child in node.get('children', []):
            if child.get('id') == task_id:
                return node
            parent = self._find_parent(task_id, child)
            if parent:
                return parent
        return None
    
    def inject_context(self) -> str:
        """Inject current context into the prompt template."""
        prompt = self.prompt_template
        
        # Get current task context
        if self.current_task_id:
            context = self.get_local_context()
            task = context.get('current', {})
            
            # Basic replacements
            prompt = prompt.replace("[PRODUCT_NAME]", "Vox2 System")
            prompt = prompt.replace("[FEATURE_NAME]", task.get('title', 'Unknown'))
            prompt = prompt.replace("[CURRENT_TASK]", task.get('description', 'No description'))
            
            # Build task tree representation
            tree_text = self._format_task_tree(context)
            prompt = prompt.replace("[TASK_TREE_REPRESENTATION]", tree_text)
            
            # Add stakeholder concerns
            stakeholder_text = self._format_stakeholders()
            # This would need a placeholder in the prompt
            
            # Add current viewpoint
            if self.mode == "constitutional":
                vp_text = self.viewpoints.get('constitutional_viewpoint', '')
            else:
                vp_text = self.viewpoints.get('execution_viewpoint', '')
            # This would need a placeholder in the prompt
        
        return prompt
    
    def _format_task_tree(self, context: Dict) -> str:
        """Format the task tree context as readable text."""
        lines = []
        current = context.get('current', {})
        
        lines.append(f"Current Task: {current.get('title', 'Unknown')} (ID: {current.get('id', 'Unknown')})")
        lines.append(f"Level: {current.get('level', 'Unknown')}")
        lines.append(f"Entity of Interest: {current.get('entity_of_interest', 'Unknown')}")
        lines.append(f"Status: {current.get('status', 'Unknown')}")
        
        if context.get('parent'):
            parent = context['parent']
            lines.append(f"\nParent: {parent.get('title', 'Unknown')} (ID: {parent.get('id', 'Unknown')})")
        
        if context.get('children'):
            lines.append("\nChildren:")
            for child in context['children']:
                lines.append(f"  - {child.get('title', 'Unknown')} (ID: {child.get('id', 'Unknown')}, Status: {child.get('status', 'Unknown')})")
        
        if context.get('dependencies'):
            lines.append(f"\nDependencies: {', '.join(context['dependencies'])}")
        
        return '\n'.join(lines)
    
    def _format_stakeholders(self) -> str:
        """Format stakeholder information as readable text."""
        lines = []
        for stakeholder in self.stakeholders.get('stakeholders', []):
            lines.append(f"- {stakeholder.get('name', 'Unknown')}: {stakeholder.get('role', 'Unknown')}")
            concerns = stakeholder.get('concerns', [])
            if concerns:
                lines.append(f"  Concerns: {', '.join(concerns[:2])}...")  # Show first 2 concerns
        return '\n'.join(lines)
    
    def switch_mode(self, new_mode: str):
        """Switch between execution and constitutional modes."""
        if new_mode in ["execution", "constitutional"]:
            old_mode = self.mode
            self.mode = new_mode
            print(f"Mode switched from {old_mode} to {new_mode}")
            self.capture_reflection(f"Mode switch: {old_mode} -> {new_mode}")
    
    def capture_reflection(self, insight: str):
        """Capture a reflection or insight."""
        self.reflection_log.append({
            'timestamp': 'now',  # Would use real timestamp
            'mode': self.mode,
            'task_id': self.current_task_id,
            'insight': insight
        })
    
    def save_reflections(self, path: str = "data/reflections.md"):
        """Save reflections to a markdown file."""
        with open(path, 'a') as f:
            f.write("\n## Reflection Session\n\n")
            for reflection in self.reflection_log:
                f.write(f"**Task**: {reflection['task_id']} | **Mode**: {reflection['mode']}\n")
                f.write(f"{reflection['insight']}\n\n")
    
    def run_cycle(self):
        """Run one cycle of agent operation."""
        print("\n=== Agent Cycle Start ===")
        
        # Navigate to a task
        if not self.current_task_id:
            self.navigate_to_task("task-001-2-1")  # Start with a specific task
        
        # Get context and inject into prompt
        prompt = self.inject_context()
        
        print(f"\nCurrent Mode: {self.mode}")
        print(f"Current Task: {self.current_task_id}")
        
        # Simulate some work
        print("\n--- Generated Prompt Preview (first 500 chars) ---")
        print(prompt[:500])
        print("...")
        
        # Check for mode switching triggers (simplified)
        if "same issue" in prompt.lower() or "pattern" in prompt.lower():
            self.capture_reflection("Detected potential pattern - considering constitutional mode")
            if self.mode == "execution":
                self.switch_mode("constitutional")
        
        # Save any reflections
        if self.reflection_log:
            self.save_reflections()
        
        print("\n=== Agent Cycle End ===")

if __name__ == '__main__':
    # Test the agent
    agent = ConstitutionalAgent()
    
    # Run a test cycle
    agent.run_cycle()
    
    # Try navigating and switching modes
    agent.navigate_to_task("task-001-2")
    agent.switch_mode("constitutional")
    agent.capture_reflection("Error handling patterns seem inconsistent across modules")
    agent.run_cycle()
    
    # Save reflections
    agent.save_reflections()