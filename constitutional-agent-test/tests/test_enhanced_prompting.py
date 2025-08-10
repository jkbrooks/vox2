import pytest
import tempfile
from unittest.mock import Mock, patch
from executive_worker.agent import ExecutiveWorker
from executive_worker.models import Ticket, DeepPlan
from executive_worker.prompting import compose_system_prompt


class TestEnhancedPrompting:
    """Test suite for Phase II enhanced system prompt generation"""
    
    @pytest.fixture
    def sample_ticket(self):
        return Ticket("123", "Test Ticket", "Test description", None)
    
    @pytest.fixture
    def sample_deep_plan(self):
        return DeepPlan(
            requirements=["Req 1", "Req 2"],
            success_criteria=["Criteria 1", "Criteria 2"],
            risks=["Risk 1"],
            strategy="Test strategy",
            estimated_complexity="medium"
        )

    def test_compose_system_prompt_includes_deep_plan(self, sample_deep_plan):
        """Test that system prompt includes deep planning context"""
        deep_plan_dict = {
            "requirements": sample_deep_plan.requirements,
            "success_criteria": sample_deep_plan.success_criteria,
            "risks": sample_deep_plan.risks,
            "strategy": sample_deep_plan.strategy,
            "estimated_complexity": sample_deep_plan.estimated_complexity
        }
        
        prompt = compose_system_prompt(
            ticket={"id": "123", "title": "Test", "description": "Test desc"},
            eoi=None,
            task_tree_snapshot={"id": "test", "title": "Test Tree"},
            workspace_summary="Test workspace",
            iso_eoi_excerpt="ISO excerpt",
            constitutional_excerpt="Constitutional excerpt",
            deep_plan=deep_plan_dict
        )
        
        assert "[DEEP_PLANNING_CONTEXT]" in prompt
        assert "Req 1" in prompt
        assert "Criteria 1" in prompt
        assert "Risk 1" in prompt
        assert "Test strategy" in prompt
        assert "medium" in prompt

    def test_compose_system_prompt_without_deep_plan(self):
        """Test system prompt generation without deep plan"""
        prompt = compose_system_prompt(
            ticket={"id": "123", "title": "Test", "description": "Test desc"},
            eoi=None,
            task_tree_snapshot={"id": "test", "title": "Test Tree"},
            workspace_summary="Test workspace",
            iso_eoi_excerpt="ISO excerpt",
            constitutional_excerpt="Constitutional excerpt",
            deep_plan=None
        )
        
        assert "[DEEP_PLANNING_CONTEXT]" not in prompt
        assert "Test desc" in prompt
        assert "Test workspace" in prompt

    def test_agent_generate_system_prompt_integration(self, sample_ticket, sample_deep_plan):
        """Test agent's system prompt generation with deep planning"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('executive_worker.agent.LLMClient') as mock_llm:
                mock_llm.return_value.model = "gpt-4o-mini"
                agent = ExecutiveWorker(tmpdir, use_enhanced=False)
                
                # Mock dependencies
                agent.task_tree = Mock()
                agent.task_tree.id = "test-tree"
                agent.task_tree.title = "Test Tree"
                agent.code.workspace_summary = Mock(return_value="Mock workspace summary")
                
                # Mock file loading functions
                with patch('executive_worker.agent.load_iso_42010_eoi_excerpt', return_value="ISO excerpt"):
                    with patch('executive_worker.agent.load_constitutional_prompt_excerpt', return_value="Constitutional excerpt"):
                        prompt = agent.generate_system_prompt(sample_ticket, None, sample_deep_plan)
                        
                        assert isinstance(prompt, str)
                        assert len(prompt) > 100
                        assert sample_ticket.title in prompt
                        assert sample_ticket.description in prompt
                        assert "[DEEP_PLANNING_CONTEXT]" in prompt
                        assert "Req 1" in prompt
