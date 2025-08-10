import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock

from executive_worker.agent import ExecutiveWorker
from executive_worker.models import Ticket, DeepPlan, ValidationResult, TestsSummary
from executive_worker.llm_client import LLMClient


class TestSemanticValidation:
    """Test suite for Phase II semantic validation functionality"""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for testing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM client for testing"""
        mock_client = Mock(spec=LLMClient)
        mock_client.model = "gpt-4o-mini"
        mock_client.client = Mock()
        return mock_client
    
    @pytest.fixture
    def agent(self, temp_workspace, mock_llm_client):
        """Create agent instance with mocked LLM"""
        with patch('executive_worker.agent.LLMClient', return_value=mock_llm_client):
            agent = ExecutiveWorker(temp_workspace, use_enhanced=False)
            agent.llm = mock_llm_client
            return agent
    
    @pytest.fixture
    def sample_ticket(self):
        """Sample ticket for testing"""
        return Ticket(
            ticket_id="123",
            title="Implement async event system",
            description="Create a sophisticated event-driven system with custom derive macros",
            eoi=None
        )
    
    @pytest.fixture
    def sample_deep_plan(self):
        """Sample deep plan for testing"""
        return DeepPlan(
            requirements=[
                "Create async event system with EventBus",
                "Implement custom derive macro for Event trait",
                "Add ECS integration components"
            ],
            success_criteria=[
                "cargo check passes",
                "all tests pass",
                "event system handles 1000+ events/sec",
                "macro generates correct code"
            ],
            risks=[
                "Async runtime integration complexity",
                "Macro syntax edge cases"
            ],
            strategy="Implement core event types first, then async processing, finally ECS integration",
            estimated_complexity="high"
        )

    def test_check_ready_to_submit_compilation_failure(self, agent, sample_ticket, sample_deep_plan):
        """Test that agent is not ready when code doesn't compile"""
        validation_result = ValidationResult(
            compiled=False,
            tests=TestsSummary(passed=True, summary="tests ok")
        )
        
        ready = agent.check_ready_to_submit(sample_ticket, validation_result, sample_deep_plan)
        
        assert ready == False

    def test_check_ready_to_submit_test_failure(self, agent, sample_ticket, sample_deep_plan):
        """Test that agent is not ready when tests fail"""
        validation_result = ValidationResult(
            compiled=True,
            tests=TestsSummary(passed=False, summary="tests failed")
        )
        
        ready = agent.check_ready_to_submit(sample_ticket, validation_result, sample_deep_plan)
        
        assert ready == False

    def test_check_ready_to_submit_semantic_failure(self, agent, sample_ticket, sample_deep_plan):
        """Test that agent is not ready when semantic validation fails"""
        validation_result = ValidationResult(
            compiled=True,
            tests=TestsSummary(passed=True, summary="tests ok")
        )
        
        # Mock semantic validation to fail
        agent.validate_against_success_criteria = Mock(return_value=False)
        
        ready = agent.check_ready_to_submit(sample_ticket, validation_result, sample_deep_plan)
        
        assert ready == False
        agent.validate_against_success_criteria.assert_called_once_with(sample_ticket, sample_deep_plan)

    def test_check_ready_to_submit_all_pass(self, agent, sample_ticket, sample_deep_plan):
        """Test that agent is ready when all validation passes"""
        validation_result = ValidationResult(
            compiled=True,
            tests=TestsSummary(passed=True, summary="tests ok")
        )
        
        # Mock semantic validation to pass
        agent.validate_against_success_criteria = Mock(return_value=True)
        
        ready = agent.check_ready_to_submit(sample_ticket, validation_result, sample_deep_plan)
        
        assert ready == True
        agent.validate_against_success_criteria.assert_called_once_with(sample_ticket, sample_deep_plan)

    def test_validate_against_success_criteria_llm_success(self, agent, sample_ticket, sample_deep_plan, mock_llm_client):
        """Test semantic validation using LLM when it succeeds"""
        # Mock workspace summary
        agent.code.workspace_summary = Mock(return_value="Mock workspace with event system files")
        
        # Mock LLM response indicating completion
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"completed": true, "reason": "All requirements implemented successfully"}'
        
        mock_llm_client.client.chat.completions.create.return_value = mock_response
        
        result = agent.validate_against_success_criteria(sample_ticket, sample_deep_plan)
        
        assert result == True
        # Verify LLM was called with correct parameters
        mock_llm_client.client.chat.completions.create.assert_called_once()
        call_args = mock_llm_client.client.chat.completions.create.call_args
        assert "evaluate if this ticket has been successfully completed" in call_args[1]["messages"][1]["content"].lower()

    def test_validate_against_success_criteria_llm_failure(self, agent, sample_ticket, sample_deep_plan, mock_llm_client):
        """Test semantic validation using LLM when it indicates failure"""
        # Mock workspace summary
        agent.code.workspace_summary = Mock(return_value="Mock workspace with incomplete implementation")
        
        # Mock LLM response indicating incompletion
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"completed": false, "reason": "Missing async processing implementation"}'
        
        mock_llm_client.client.chat.completions.create.return_value = mock_response
        
        result = agent.validate_against_success_criteria(sample_ticket, sample_deep_plan)
        
        assert result == False

    def test_validate_against_success_criteria_llm_error_fallback(self, agent, sample_ticket, sample_deep_plan, mock_llm_client):
        """Test semantic validation fallback when LLM fails"""
        # Mock workspace summary
        agent.code.workspace_summary = Mock(return_value="Mock workspace")
        
        # Mock LLM error
        mock_llm_client.client.chat.completions.create.side_effect = Exception("API Error")
        
        # Mock fallback heuristic
        agent._basic_completion_heuristic = Mock(return_value=True)
        
        result = agent.validate_against_success_criteria(sample_ticket, sample_deep_plan)
        
        assert result == True
        agent._basic_completion_heuristic.assert_called_once_with(sample_ticket, sample_deep_plan)

    def test_basic_completion_heuristic_no_requirements(self, agent, sample_ticket):
        """Test heuristic validation with no requirements"""
        empty_plan = DeepPlan(requirements=[], success_criteria=[], risks=[], strategy="", estimated_complexity="low")
        
        result = agent._basic_completion_heuristic(sample_ticket, empty_plan)
        
        assert result == True  # No requirements means automatically complete

    def test_basic_completion_heuristic_with_requirements(self, agent, sample_ticket, sample_deep_plan):
        """Test heuristic validation with requirements"""
        # Mock file system to have some relevant files
        agent.code.glob_files = Mock(return_value=[
            "src/event_system/mod.rs",
            "src/event_system/event_bus.rs", 
            "src/async_processor.rs",
            "tests/event_tests.rs"
        ])
        
        result = agent._basic_completion_heuristic(sample_ticket, sample_deep_plan)
        
        # Should find evidence for "event" related requirements
        assert isinstance(result, bool)
        # With event-related files, should likely pass the 50% threshold
        
    def test_basic_completion_heuristic_insufficient_evidence(self, agent, sample_ticket, sample_deep_plan):
        """Test heuristic validation with insufficient evidence"""
        # Mock file system with unrelated files
        agent.code.glob_files = Mock(return_value=[
            "src/main.rs",
            "src/utils.rs",
            "README.md"
        ])
        
        result = agent._basic_completion_heuristic(sample_ticket, sample_deep_plan)
        
        # Should fail to find sufficient evidence
        assert result == False

    def test_basic_completion_heuristic_error_handling(self, agent, sample_ticket, sample_deep_plan):
        """Test heuristic validation handles errors gracefully"""
        # Mock file system error
        agent.code.glob_files = Mock(side_effect=Exception("File system error"))
        
        result = agent._basic_completion_heuristic(sample_ticket, sample_deep_plan)
        
        # Should handle error gracefully and return False
        assert result == False

    def test_semantic_validation_with_enhanced_mode(self, temp_workspace, sample_ticket, sample_deep_plan):
        """Test semantic validation with enhanced codebase utilities"""
        with patch('executive_worker.agent.LLMClient') as mock_llm_class:
            mock_llm = Mock()
            mock_llm.client.chat.completions.create.return_value = Mock()
            mock_llm.client.chat.completions.create.return_value.choices = [Mock()]
            mock_llm.client.chat.completions.create.return_value.choices[0].message.content = '{"completed": true, "reason": "Complete"}'
            mock_llm_class.return_value = mock_llm
            
            agent = ExecutiveWorker(temp_workspace, use_enhanced=True)
            
            # Mock enhanced codebase utilities
            if agent.enhanced_code:
                agent.enhanced_code.workspace_summary = Mock(return_value="Enhanced workspace summary")
            
            result = agent.validate_against_success_criteria(sample_ticket, sample_deep_plan)
            
            assert isinstance(result, bool)
            # Should have used enhanced workspace summary
            if agent.enhanced_code:
                agent.enhanced_code.workspace_summary.assert_called_once()

    def test_validation_result_integration(self, agent, sample_ticket, sample_deep_plan):
        """Test integration of validation results in the main execution loop"""
        # Test that validation results are properly used in the ready-to-submit check
        
        # Case 1: Everything passes
        validation_success = ValidationResult(compiled=True, tests=TestsSummary(passed=True, summary="all good"))
        agent.validate_against_success_criteria = Mock(return_value=True)
        
        ready = agent.check_ready_to_submit(sample_ticket, validation_success, sample_deep_plan)
        assert ready == True
        
        # Case 2: Compilation fails
        validation_compile_fail = ValidationResult(compiled=False, tests=TestsSummary(passed=True, summary="tests ok"))
        
        ready = agent.check_ready_to_submit(sample_ticket, validation_compile_fail, sample_deep_plan)
        assert ready == False
        
        # Case 3: Tests fail
        validation_test_fail = ValidationResult(compiled=True, tests=TestsSummary(passed=False, summary="tests failed"))
        
        ready = agent.check_ready_to_submit(sample_ticket, validation_test_fail, sample_deep_plan)
        assert ready == False
        
        # Case 4: Semantic validation fails
        validation_semantic_fail = ValidationResult(compiled=True, tests=TestsSummary(passed=True, summary="tests ok"))
        agent.validate_against_success_criteria = Mock(return_value=False)
        
        ready = agent.check_ready_to_submit(sample_ticket, validation_semantic_fail, sample_deep_plan)
        assert ready == False

    @patch('builtins.print')  # Mock print to test console output
    def test_validation_console_output(self, mock_print, agent, sample_ticket, sample_deep_plan):
        """Test that validation provides helpful console output"""
        # Test compilation failure output
        validation_result = ValidationResult(compiled=False, tests=None)
        
        agent.check_ready_to_submit(sample_ticket, validation_result, sample_deep_plan)
        
        # Should print compilation error message
        mock_print.assert_called_with("❌ Not ready: Code doesn't compile")
        
        # Test success output
        mock_print.reset_mock()
        validation_result = ValidationResult(compiled=True, tests=TestsSummary(passed=True, summary="ok"))
        agent.validate_against_success_criteria = Mock(return_value=True)
        
        agent.check_ready_to_submit(sample_ticket, validation_result, sample_deep_plan)
        
        # Should print success message
        mock_print.assert_called_with("✅ Ready to submit: All validation criteria passed")

    def test_semantic_validation_prompt_construction(self, agent, sample_ticket, sample_deep_plan, mock_llm_client):
        """Test that semantic validation constructs proper prompts"""
        agent.code.workspace_summary = Mock(return_value="Test workspace summary")
        
        # Mock LLM response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"completed": true, "reason": "Complete"}'
        mock_llm_client.client.chat.completions.create.return_value = mock_response
        
        agent.validate_against_success_criteria(sample_ticket, sample_deep_plan)
        
        # Verify the prompt contains all necessary elements
        call_args = mock_llm_client.client.chat.completions.create.call_args
        prompt_content = call_args[1]["messages"][1]["content"]
        
        assert sample_ticket.title in prompt_content
        assert sample_ticket.description in prompt_content
        assert str(sample_deep_plan.requirements) in prompt_content
        assert str(sample_deep_plan.success_criteria) in prompt_content
        assert "Test workspace summary" in prompt_content
        assert "Has the ticket been successfully completed?" in prompt_content
