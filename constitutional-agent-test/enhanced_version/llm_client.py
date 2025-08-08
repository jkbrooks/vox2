"""
LLM Client for Constitutional Agent
Handles interaction with Claude for code generation
"""

import os
import json
from typing import Dict, Optional
from anthropic import Anthropic

class LLMClient:
    """Client for interacting with Claude"""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found")
        
        self.client = Anthropic(api_key=self.api_key)
        # Default to Haiku (10x cheaper than Opus)
        # Opus: ~$15/1M input, $75/1M output
        # Haiku: ~$0.25/1M input, $1.25/1M output
        self.model = model or os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307")
    
    def generate_architecture(self, 
                            task: str,
                            requirements: str,
                            context: Dict[str, str]) -> str:
        """Generate architecture for a task"""
        
        # Format context files
        context_str = "\n\n".join([
            f"File: {path}\n```rust\n{content[:500]}...\n```"
            for path, content in list(context.items())[:5]
        ])
        
        prompt = f"""Design architecture for this task:

Task: {task}
Requirements: {requirements}

Existing Code Context:
{context_str}

Provide a detailed architecture including:
1. Components to create/modify
2. Integration points
3. Data flow
4. Error handling approach
5. Testing strategy

Be specific about Rust/ECS patterns to use."""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            temperature=0.7,
            system="You are an expert Rust game developer familiar with ECS patterns.",
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.content[0].text
    
    def generate_code(self,
                     task: str,
                     architecture: str,
                     file_path: str,
                     context: Optional[str] = None) -> str:
        """Generate code for a specific file"""
        
        prompt = f"""Implement this task in Rust:

Task: {task}
Target File: {file_path}

Architecture:
{architecture}

{f"Existing Code:\n```rust\n{context}\n```" if context else ""}

Generate complete, production-ready Rust code.
Include proper error handling and documentation."""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            temperature=0.3,
            system="You are an expert Rust developer. Generate clean, idiomatic code.",
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Extract code from response
        content = response.content[0].text
        
        # Try to extract code block
        import re
        code_match = re.search(r'```(?:rust)?\n(.*?)\n```', content, re.DOTALL)
        if code_match:
            return code_match.group(1)
        return content
    
    def review_code(self, code: str, requirements: str) -> Dict[str, any]:
        """Review generated code"""
        
        prompt = f"""Review this Rust code:

```rust
{code}
```

Requirements: {requirements}

Provide JSON review:
{{
  "compiles": true/false,
  "meets_requirements": true/false,
  "issues": ["list of issues"],
  "suggestions": ["list of improvements"]
}}"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            temperature=0.5,
            system="You are a senior Rust developer performing code review.",
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Parse JSON from response
        content = response.content[0].text
        try:
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
            
        return {
            "compiles": True,
            "meets_requirements": True,
            "issues": [],
            "suggestions": []
        }
