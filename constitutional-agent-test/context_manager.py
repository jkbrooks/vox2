"""
Context Manager for Constitutional Agent
Handles dynamic context injection with token budget awareness
"""

import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import tiktoken

# Initialize tokenizer for token counting
try:
    tokenizer = tiktoken.get_encoding("cl100k_base")  # GPT-4 encoding
except:
    tokenizer = None  # Fallback if tiktoken fails

class Priority(Enum):
    """Priority levels for context elements"""
    CRITICAL = 1    # Must include (core definitions, current task)
    HIGH = 2        # Should include (local context, active stakeholders)
    MEDIUM = 3      # Nice to have (related insights, patterns)
    LOW = 4         # Optional (historical data, examples)

@dataclass
class ContextElement:
    """Represents a piece of context that could be injected"""
    name: str
    content: str
    priority: Priority
    token_count: int = 0
    relevance_score: float = 1.0  # 0-1, based on current EoI/mode
    dependencies: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if self.token_count == 0:
            self.token_count = estimate_tokens(self.content)

def estimate_tokens(text: str) -> int:
    """Estimate token count for a piece of text"""
    if tokenizer:
        # Use tiktoken for accurate counting
        return len(tokenizer.encode(text))
    else:
        # Fallback: rough estimate of 1 token per 4 characters
        return len(text) // 4

class ContextManager:
    """Manages context injection with token budget awareness"""
    
    def __init__(self, 
                 base_prompt_path: str,
                 token_budget: int = 10000,
                 mode: str = "execution"):
        self.base_prompt = self._load_base_prompt(base_prompt_path)
        self.token_budget = token_budget
        self.mode = mode
        self.current_eoi = None
        self.context_elements: Dict[str, ContextElement] = {}
        self.used_tokens = 0
        
    def _load_base_prompt(self, path: str) -> str:
        """Load the base constitutional prompt"""
        with open(path, 'r') as f:
            return f.read()
    
    def set_entity_of_interest(self, eoi: Dict[str, Any]):
        """Set the current Entity of Interest and recalculate relevance"""
        self.current_eoi = eoi
        self._recalculate_relevance()
    
    def set_mode(self, mode: str):
        """Switch between execution and constitutional modes"""
        self.mode = mode
        self._recalculate_relevance()
    
    def _recalculate_relevance(self):
        """Recalculate relevance scores based on current EoI and mode"""
        if not self.current_eoi:
            return
        
        for element in self.context_elements.values():
            # Base relevance on mode
            if self.mode == "constitutional":
                if "ISO" in element.name or "stakeholder" in element.name:
                    element.relevance_score = 0.9
                elif "viewpoint" in element.name:
                    element.relevance_score = 0.8
                else:
                    element.relevance_score = 0.5
            else:  # execution mode
                if "task" in element.name.lower() or "current" in element.name.lower():
                    element.relevance_score = 0.9
                elif "ISO" in element.name:
                    element.relevance_score = 0.3  # Less relevant in execution
                else:
                    element.relevance_score = 0.6
            
            # Adjust based on EoI level
            eoi_level = self.current_eoi.get('level', 'L5')
            if eoi_level in ['L1', 'L2']:  # System/Coordination level
                if "architecture" in element.name.lower():
                    element.relevance_score *= 1.2
            elif eoi_level in ['L4', 'L5']:  # Feature/Task level
                if "execution" in element.name.lower():
                    element.relevance_score *= 1.2
            
            # Cap at 1.0
            element.relevance_score = min(1.0, element.relevance_score)
    
    def add_context_element(self, name: str, content: str, 
                           priority: Priority, dependencies: List[str] = None):
        """Add a context element to the pool"""
        self.context_elements[name] = ContextElement(
            name=name,
            content=content,
            priority=priority,
            dependencies=dependencies or []
        )
    
    def build_prompt(self) -> Tuple[str, Dict[str, Any]]:
        """Build the final prompt within token budget"""
        # Start with base prompt
        prompt = self.base_prompt
        base_tokens = estimate_tokens(prompt)
        remaining_budget = self.token_budget - base_tokens
        
        # Collect and prioritize elements
        elements = list(self.context_elements.values())
        
        # Sort by priority and relevance
        elements.sort(key=lambda x: (x.priority.value, -x.relevance_score))
        
        # Track what we include
        included = {}
        included_names = set()
        
        # First pass: Include all CRITICAL elements
        for element in elements:
            if element.priority == Priority.CRITICAL:
                if element.token_count <= remaining_budget:
                    included[element.name] = element
                    included_names.add(element.name)
                    remaining_budget -= element.token_count
        
        # Second pass: Include HIGH priority by relevance
        for element in elements:
            if element.priority == Priority.HIGH and element.name not in included_names:
                # Check dependencies
                deps_met = all(dep in included_names for dep in element.dependencies)
                if deps_met and element.token_count <= remaining_budget:
                    included[element.name] = element
                    included_names.add(element.name)
                    remaining_budget -= element.token_count
        
        # Third pass: Include MEDIUM priority if space
        for element in elements:
            if element.priority == Priority.MEDIUM and element.name not in included_names:
                if element.relevance_score > 0.7:  # Only highly relevant medium priority
                    deps_met = all(dep in included_names for dep in element.dependencies)
                    if deps_met and element.token_count <= remaining_budget:
                        included[element.name] = element
                        included_names.add(element.name)
                        remaining_budget -= element.token_count
        
        # Fourth pass: Include LOW priority only if lots of space
        if remaining_budget > 2000:  # Only if we have lots of room
            for element in elements:
                if element.priority == Priority.LOW and element.name not in included_names:
                    if element.relevance_score > 0.8:
                        deps_met = all(dep in included_names for dep in element.dependencies)
                        if deps_met and element.token_count <= remaining_budget:
                            included[element.name] = element
                            included_names.add(element.name)
                            remaining_budget -= element.token_count
        
        # Inject the selected content into the prompt
        prompt = self._inject_content(prompt, included)
        
        # Build metadata about what was included
        metadata = {
            'total_tokens': self.token_budget - remaining_budget,
            'remaining_budget': remaining_budget,
            'included_elements': list(included_names),
            'excluded_elements': [e.name for e in elements if e.name not in included_names],
            'mode': self.mode,
            'eoi': self.current_eoi
        }
        
        return prompt, metadata
    
    def _inject_content(self, prompt: str, included: Dict[str, ContextElement]) -> str:
        """Inject the selected content into the prompt placeholders"""
        # Map element names to placeholders
        placeholder_map = {
            'product_description': '[PRODUCT_DESCRIPTION]',
            'feature_context': '[FEATURE_CONTEXT]',
            'task_details': '[TASK_DETAILS]',
            'current_entity': '[CURRENT_ENTITY_OF_INTEREST]',
            'task_tree': '[TASK_TREE_REPRESENTATION]',
            'stakeholders': '[STAKEHOLDER_DEFINITIONS_AND_CONCERNS]',
            'viewpoints': '[CURRENT_VIEWPOINTS_AND_VIEWS]',
            'correspondences': '[RELEVANT_RELATIONSHIPS_AND_DEPENDENCIES]',
            'insights': '[CONSTITUTIONAL_INSIGHTS_FROM_OTHER_AGENTS]',
        }
        
        for name, element in included.items():
            # Find the right placeholder
            for key, placeholder in placeholder_map.items():
                if key in name.lower():
                    prompt = prompt.replace(placeholder, element.content)
                    break
        
        # Clear any remaining placeholders that weren't filled
        for placeholder in placeholder_map.values():
            if placeholder in prompt:
                prompt = prompt.replace(placeholder, f"<!-- {placeholder} not included due to token budget -->")
        
        return prompt

class DynamicContextInjector:
    """
    Higher-level class that manages context across different scenarios
    """
    
    def __init__(self, data_dir: Path, token_budget: int = 10000):
        self.data_dir = data_dir
        self.token_budget = token_budget
        self.context_manager = None
        self.task_tree = None
        self.stakeholders = None
        self.viewpoints = {}
        self.insights_log = []
        
    def load_data(self):
        """Load all available data sources"""
        # Load task tree
        tree_path = self.data_dir / "sample_task_tree.yaml"
        if tree_path.exists():
            with open(tree_path, 'r') as f:
                self.task_tree = yaml.safe_load(f)
        
        # Load stakeholders
        stakeholder_path = self.data_dir / "stakeholders.yaml"
        if stakeholder_path.exists():
            with open(stakeholder_path, 'r') as f:
                self.stakeholders = yaml.safe_load(f)
        
        # Load viewpoints
        viewpoint_dir = self.data_dir / "viewpoints"
        if viewpoint_dir.exists():
            for vp_file in viewpoint_dir.glob("*.md"):
                with open(vp_file, 'r') as f:
                    self.viewpoints[vp_file.stem] = f.read()
    
    def prepare_context_for_task(self, task_id: str, mode: str = "execution") -> Tuple[str, Dict]:
        """
        Prepare context injection for a specific task
        This is the main entry point for the agent
        """
        # Find the task in the tree
        task = self._find_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        # Initialize context manager
        self.context_manager = ContextManager(
            base_prompt_path="prompts/constitutional_system_prompt.md",
            token_budget=self.token_budget,
            mode=mode
        )
        
        # Set the Entity of Interest
        self.context_manager.set_entity_of_interest(task)
        
        # Add context elements based on the task and mode
        self._add_task_context(task)
        self._add_stakeholder_context(task)
        self._add_viewpoint_context(mode)
        self._add_tree_context(task)
        
        if mode == "constitutional":
            self._add_iso_context()
            self._add_insight_context()
        
        # Build and return the prompt
        return self.context_manager.build_prompt()
    
    def _find_task(self, task_id: str, node: Dict = None) -> Optional[Dict]:
        """Find a task in the tree by ID"""
        if node is None:
            node = self.task_tree.get('root', {})
        
        if node.get('id') == task_id:
            return node
        
        for child in node.get('children', []):
            result = self._find_task(task_id, child)
            if result:
                return result
        return None
    
    def _add_task_context(self, task: Dict):
        """Add task-specific context"""
        # Current task details - CRITICAL
        self.context_manager.add_context_element(
            name="task_details",
            content=f"Task: {task.get('title', 'Unknown')}\n"
                   f"Description: {task.get('description', 'No description')}\n"
                   f"Level: {task.get('level', 'Unknown')}\n"
                   f"Status: {task.get('status', 'Unknown')}",
            priority=Priority.CRITICAL
        )
        
        # Entity of Interest - CRITICAL
        self.context_manager.add_context_element(
            name="current_entity",
            content=task.get('entity_of_interest', 'Unknown entity'),
            priority=Priority.CRITICAL
        )
    
    def _add_stakeholder_context(self, task: Dict):
        """Add relevant stakeholder context"""
        if not self.stakeholders:
            return
        
        # Filter stakeholders based on task level
        task_level = task.get('level', 'L5')
        relevant_stakeholders = []
        
        for stakeholder in self.stakeholders.get('stakeholders', []):
            # Simple relevance: include all for L1-L2, filter for L3-L5
            if task_level in ['L1', 'L2']:
                relevant_stakeholders.append(stakeholder)
            elif 'agent' in stakeholder.get('id', '').lower():
                relevant_stakeholders.append(stakeholder)
            elif task_level == 'L3' and 'human' in stakeholder.get('id', '').lower():
                relevant_stakeholders.append(stakeholder)
        
        if relevant_stakeholders:
            content = "Relevant Stakeholders:\n"
            for sh in relevant_stakeholders:
                content += f"- {sh.get('name', 'Unknown')}: {sh.get('role', 'Unknown')}\n"
                concerns = sh.get('concerns', [])[:2]  # First 2 concerns
                if concerns:
                    content += f"  Concerns: {', '.join(concerns)}\n"
            
            self.context_manager.add_context_element(
                name="stakeholders",
                content=content,
                priority=Priority.HIGH
            )
    
    def _add_viewpoint_context(self, mode: str):
        """Add appropriate viewpoint based on mode"""
        viewpoint_name = f"{mode}_viewpoint"
        if viewpoint_name in self.viewpoints:
            self.context_manager.add_context_element(
                name="viewpoints",
                content=self.viewpoints[viewpoint_name],
                priority=Priority.HIGH if mode == "constitutional" else Priority.MEDIUM
            )
    
    def _add_tree_context(self, task: Dict):
        """Add task tree context around the current task"""
        # Build local tree context
        tree_content = f"Current Task: {task.get('title', 'Unknown')}\n"
        
        # Add parent if exists (simplified - would need proper parent tracking)
        tree_content += "\nTask Hierarchy:\n"
        tree_content += f"└── {task.get('title', 'Unknown')} (current)\n"
        
        # Add children if any
        children = task.get('children', [])
        if children:
            tree_content += "    Children:\n"
            for child in children[:3]:  # Limit to 3 children
                tree_content += f"    ├── {child.get('title', 'Unknown')}\n"
        
        # Add dependencies
        deps = task.get('dependencies', [])
        if deps:
            tree_content += f"\nDependencies: {', '.join(deps)}\n"
        
        self.context_manager.add_context_element(
            name="task_tree",
            content=tree_content,
            priority=Priority.HIGH
        )
    
    def _add_iso_context(self):
        """Add ISO/IEEE 42010 context for constitutional mode"""
        # This would load from a separate file in production
        iso_content = """
Key ISO/IEEE 42010 Concepts:
- Architecture: Fundamental concepts or properties of an entity
- Stakeholder: Individual/group with interest in the entity
- Concern: Interest pertaining to the entity
- Viewpoint: Conventions for constructing and using views
- Correspondence: Relation between AD elements
"""
        self.context_manager.add_context_element(
            name="iso_definitions",
            content=iso_content,
            priority=Priority.MEDIUM
        )
    
    def _add_insight_context(self):
        """Add recent constitutional insights"""
        if self.insights_log:
            recent_insights = self.insights_log[-3:]  # Last 3 insights
            content = "Recent Constitutional Insights:\n"
            for insight in recent_insights:
                content += f"- {insight}\n"
            
            self.context_manager.add_context_element(
                name="insights",
                content=content,
                priority=Priority.LOW
            )

# Example usage
if __name__ == "__main__":
    injector = DynamicContextInjector(Path("data"))
    injector.load_data()
    
    # Prepare context for execution mode
    prompt, metadata = injector.prepare_context_for_task("task-001-2-1", mode="execution")
    print(f"Execution mode - Tokens used: {metadata['total_tokens']}")
    print(f"Included: {metadata['included_elements']}")
    
    # Switch to constitutional mode
    prompt, metadata = injector.prepare_context_for_task("task-001-2-1", mode="constitutional")
    print(f"\nConstitutional mode - Tokens used: {metadata['total_tokens']}")
    print(f"Included: {metadata['included_elements']}")
