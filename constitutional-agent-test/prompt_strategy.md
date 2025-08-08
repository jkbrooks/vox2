# Dynamic Prompt Strategy for Constitutional Agents

**Version: 1.0** (Design Specification)  
**Status: Not fully implemented in context_manager.py (v0.5)**

## Implementation Note
The context_manager.py currently implements a simplified version (v0.5) of this strategy for development brevity. Key concepts like triggers, token allocation, and prioritization are present but not all advanced features (caching, learning loops, versioning) are wired in. Future iterations will close this gap based on empirical testing and constitutional reflections.

## Core Principle: Context Should Match Cognitive Focus

The prompt should change not just when the Entity of Interest (EoI) changes, but when the agent's cognitive needs shift. This creates several trigger points for prompt updates.

## Prompt Change Triggers

### 1. Entity of Interest Changes (Primary Trigger)
When the agent shifts focus to a different entity, the entire context should reorganize:
- **System → Subsystem**: Remove high-level governance, add implementation details
- **Task → Feature**: Expand scope, include more stakeholders
- **Technical → Conceptual**: Switch from code patterns to design principles

### 2. Mode Transitions (Secondary Trigger)
Mode changes dramatically alter what context is valuable:
- **Execution → Constitutional**: Load ISO definitions, stakeholder frameworks, correspondence patterns
- **Constitutional → Execution**: Load tool documentation, code patterns, success criteria

### 3. Cognitive Load Indicators (Adaptive Triggers)
The agent's behavior can signal when context needs adjustment:
- **Repetition**: If agent repeats questions/mistakes → needs different context
- **Confusion**: Ambiguous responses → needs clarification context
- **Breakthrough**: New insight → capture and reinforce with related context

### 4. Task Phase Transitions
Different phases of work need different context:
- **Planning**: Task tree, dependencies, stakeholder concerns
- **Implementation**: Tools, patterns, examples
- **Review**: Quality criteria, architectural principles
- **Reflection**: Historical patterns, insights from other agents

## Token Budget Allocation Strategy

### Dynamic Allocation Based on Mode and Phase

```
Total Budget: 10,000 tokens

Base Prompt (always present): 2,000 tokens
- Core definitions
- Mode triggers
- Basic framework

Dynamic Pool: 8,000 tokens allocated by priority
```

#### Execution Mode Allocation
```
Priority 1 (3,000 tokens):
- Current task details
- Immediate dependencies
- Tool documentation
- Success criteria

Priority 2 (2,500 tokens):
- Local task tree context
- Recent execution history
- Code patterns
- Error handling

Priority 3 (1,500 tokens):
- Stakeholder concerns (filtered)
- Quality guidelines
- Performance considerations

Priority 4 (1,000 tokens):
- Examples
- Historical patterns
- Alternative approaches
```

#### Constitutional Mode Allocation
```
Priority 1 (3,500 tokens):
- Full ISO/IEEE definitions
- Current EoI analysis
- Stakeholder framework
- Concern mappings

Priority 2 (2,500 tokens):
- Viewpoint definitions
- Correspondence patterns
- Recent insights
- Architectural principles

Priority 3 (1,500 tokens):
- Historical decisions
- Pattern library
- Cross-system examples

Priority 4 (500 tokens):
- Meta-insights
- Evolution patterns
```

## Content Prioritization Algorithm

### Relevance Scoring Formula
```python
relevance = base_priority * mode_modifier * recency_factor * eoi_alignment * usage_frequency

Where:
- base_priority: Inherent importance (1.0 for critical, 0.5 for optional)
- mode_modifier: How relevant to current mode (0.3-1.0)
- recency_factor: How recently referenced (decay over time)
- eoi_alignment: How closely related to current EoI (0.1-1.0)
- usage_frequency: How often this type helps (learned over time)
```

### Smart Exclusion Rules
Don't include content that:
1. Was in the last 3 prompts unchanged (agent already knows it)
2. Has relevance score < 0.3
3. Depends on excluded content
4. Contradicts current mode/phase

## Prompt Versioning Strategy

### Incremental Updates
Not every trigger requires a full prompt rebuild:

**Minor Update** (append/replace sections):
- New insight discovered
- Task status change
- Stakeholder concern added

**Major Update** (rebuild from base):
- EoI change
- Mode transition
- Phase transition

**Evolutionary Update** (modify base):
- Repeated pattern detected
- Consistent mode switching at certain points
- Agent requests specific changes

### Version Tracking
Each prompt generation should track:
```json
{
  "version": "1.2.3",
  "trigger": "eoi_change",
  "timestamp": "2024-01-08T10:30:00Z",
  "eoi": "task-001-2-1",
  "mode": "execution",
  "phase": "implementation",
  "tokens_used": 8750,
  "elements_included": ["task_details", "stakeholders_filtered", "tools"],
  "elements_excluded": ["iso_full", "historical_patterns"],
  "exclusion_reasons": {
    "iso_full": "execution_mode",
    "historical_patterns": "token_budget"
  }
}
```

## Learning and Adaptation

### Tracking What Works
Monitor which context elements correlate with:
- Successful task completion
- Insightful constitutional observations
- Smooth mode transitions
- Minimal repetition/confusion

### Adaptive Weights
Adjust relevance scoring based on outcomes:
```python
# After successful task with certain context
for element in included_elements:
    element.success_weight *= 1.1  # Increase weight
    
# After confusion/failure
for element in included_elements:
    if element.name in confusion_indicators:
        element.success_weight *= 0.9  # Decrease weight
```

### Pattern Recognition
Identify recurring patterns:
- "ISO definitions always needed when switching to constitutional at L1-L2"
- "Tool docs rarely used in tasks with 'refactor' in title"
- "Stakeholder concerns critical for 'implement' tasks"

## Implementation Considerations

### 1. Lazy Loading
Don't load everything upfront:
```python
class LazyContextElement:
    def __init__(self, name, loader_func):
        self.name = name
        self.loader_func = loader_func
        self._content = None
        self._tokens = None
    
    @property
    def content(self):
        if self._content is None:
            self._content = self.loader_func()
        return self._content
```

### 2. Context Caching
Cache frequently used combinations:
```python
cache_key = f"{eoi_id}_{mode}_{phase}"
if cache_key in context_cache:
    return context_cache[cache_key]
```

### 3. Streaming Context
For very large contexts, stream in sections:
```python
def stream_context(base_prompt, context_elements):
    yield base_prompt
    for element in priority_order(context_elements):
        if within_budget(element):
            yield element.content
```

## Practical Examples

### Example 1: Task Execution Start
```
Trigger: New task selected
EoI: task-001-2-1 (L5 - Define Error Type Hierarchy)
Mode: Execution
Phase: Planning

Include:
- Task details (500 tokens)
- Parent task context (300 tokens)
- Dependencies (200 tokens)
- Success criteria (400 tokens)
- Relevant code patterns (800 tokens)
- Stakeholders: agent-executor, system-itself (600 tokens)

Exclude:
- ISO definitions (not needed for execution)
- Other agents' insights (not relevant yet)
- Historical patterns (no similar tasks identified)
```

### Example 2: Constitutional Reflection
```
Trigger: Pattern detected (3rd similar error)
EoI: Shifts to L3 (Error Handling System)
Mode: Constitutional
Phase: Analysis

Include:
- ISO architecture definition (800 tokens)
- Stakeholder framework (1200 tokens)
- Error handling viewpoint (1000 tokens)
- Recent error patterns (600 tokens)
- Correspondence analysis (500 tokens)
- Similar insights from other agents (400 tokens)

Exclude:
- Implementation details (too specific)
- Tool documentation (not needed for analysis)
- Unrelated task tree branches
```

### Example 3: Mode Transition
```
Trigger: Completion of task, switching to reflection
EoI: Same (task-001-2-1)
Mode: Execution → Constitutional
Phase: Implementation → Reflection

Remove:
- Tool documentation
- Code examples
- Implementation patterns

Add:
- Reflection protocol
- Pattern recognition framework
- Insight capture template
- Related constitutional insights

Modify:
- Stakeholder view: execution concerns → architectural concerns
- Task view: details → patterns
```

## Success Metrics

Track these to evaluate the dynamic prompt strategy:

1. **Token Efficiency**: Average tokens used vs budget
2. **Context Hit Rate**: How often included context is referenced
3. **Mode Transition Smoothness**: Time/tokens to productive work after switch
4. **Insight Quality**: Constitutional insights per token of ISO content
5. **Task Success Rate**: Correlation with context configurations
6. **Repetition Rate**: How often agent asks for missing context

## Future Enhancements

1. **Predictive Context Loading**: Anticipate next likely context needs
2. **Multi-Agent Context Sharing**: Pool insights across agents
3. **Context Compression**: Summarize verbose elements while preserving meaning
4. **Adaptive Tokenization**: Use different encoding for different content types
5. **Context Versioning**: Track which context versions led to breakthroughs
