import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from executive_worker.agent import ExecutiveWorker
from executive_worker.models import Ticket, DeepPlan, ValidationResult, TestsSummary


class TestPhase2Integration:
    """Integration tests for Phase II intelligence improvements"""
    
    @pytest.fixture
    def temp_workspace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create some basic files for testing
            os.makedirs(os.path.join(tmpdir, "src"), exist_ok=True)
            with open(os.path.join(tmpdir, "src", "main.rs"), "w") as f:
                f.write("fn main() { println!('Hello'); }")
            yield tmpdir

    @pytest.fixture
    def mock_llm_responses(self):
        """Mock all LLM responses for integration testing"""
        return {
            'requirements': ["Create event system", "Add async processing"],
            'success_criteria': ["Code compiles", "Tests pass"],
            'risks': ["Async complexity"],
            'strategy': "Implement incrementally",
            'plan': [
                {"description": "Create event module", "kind": "shell", "args": {"cmd": "mkdir -p src/events"}},
                {"description": "Add event types", "kind": "edit", "args": {"edits": [{"path": "src/events/mod.rs", "find": "", "replace": "pub mod events;"}]}}
            ],
            'eoi_choice': {"label": "Event System", "path": "src/events/mod.rs"},
            'semantic_validation': {"completed": True, "reason": "All requirements met"}
        }

    def test_full_phase2_workflow(self, temp_workspace, mock_llm_responses):
        """Test the complete Phase II workflow from ticket to completion"""
        with patch('executive_worker.agent.LLMClient') as mock_llm_class:
            # Setup mock LLM
            mock_llm = Mock()
            mock_llm.model = "gpt-4o-mini"
            mock_llm.client = Mock()
            
            # Mock all LLM methods
            mock_llm.analyze_requirements.return_value = mock_llm_responses['requirements']
            mock_llm.define_success_criteria.return_value = mock_llm_responses['success_criteria']
            mock_llm.assess_complexity_and_risks.return_value = mock_llm_responses['risks']
            mock_llm.create_strategy.return_value = mock_llm_responses['strategy']
            mock_llm.create_plan_from_prompt.return_value = []  # Empty plan for simplicity
            mock_llm.choose_eoi.return_value = mock_llm_responses['eoi_choice']
            
            # Mock semantic validation
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = '{"completed": true, "reason": "All requirements met"}'
            mock_llm.client.chat.completions.create.return_value = mock_response
            
            mock_llm_class.return_value = mock_llm
            
            # Create agent
            agent = ExecutiveWorker(temp_workspace, use_enhanced=False)
            
            # Create test ticket
            ticket = Ticket("test-123", "Implement Event System", "Create an async event system with proper error handling", None)
            
            # Mock validation to pass quickly
            agent.validate_changes = Mock(return_value=ValidationResult(compiled=True, tests=TestsSummary(passed=True, summary="ok")))
            
            # Execute ticket (this should complete the full Phase II workflow)
            run_log = agent.execute_ticket(ticket)
            
            # Verify Phase II components were executed
            assert run_log.deep_plan is not None
            assert run_log.deep_plan.requirements == mock_llm_responses['requirements']
            assert run_log.deep_plan.success_criteria == mock_llm_responses['success_criteria']
            assert run_log.deep_plan.risks == mock_llm_responses['risks']
            assert run_log.deep_plan.strategy == mock_llm_responses['strategy']
            
            # Verify workflow completed
            assert run_log.status == "completed"
            assert run_log.end_ts is not None
            
            # Verify LLM methods were called
            mock_llm.analyze_requirements.assert_called_once()
            mock_llm.define_success_criteria.assert_called_once()
            mock_llm.assess_complexity_and_risks.assert_called_once()
            mock_llm.create_strategy.assert_called_once()

    def test_deep_planning_affects_system_prompt(self, temp_workspace, mock_llm_responses):
        """Test that deep planning context is included in system prompts"""
        with patch('executive_worker.agent.LLMClient') as mock_llm_class:
            mock_llm = Mock()
            mock_llm.analyze_requirements.return_value = ["Test requirement"]
            mock_llm.define_success_criteria.return_value = ["Test criteria"]
            mock_llm.assess_complexity_and_risks.return_value = ["Test risk"]
            mock_llm.create_strategy.return_value = "Test strategy"
            mock_llm_class.return_value = mock_llm
            
            agent = ExecutiveWorker(temp_workspace, use_enhanced=False)
            
            # Mock dependencies
            agent.task_tree = Mock()
            agent.task_tree.id = "test"
            agent.task_tree.title = "Test"
            agent.code.workspace_summary = Mock(return_value="workspace")
            
            ticket = Ticket("test", "Test", "Test description", None)
            deep_plan = agent.analyze_requirements_and_plan(ticket)
            
            # Mock file loading
            with patch('executive_worker.agent.load_iso_42010_eoi_excerpt', return_value="ISO"):
                with patch('executive_worker.agent.load_constitutional_prompt_excerpt', return_value="Constitutional"):
                    prompt = agent.generate_system_prompt(ticket, None, deep_plan)
                    
                    # Verify deep planning context is in prompt
                    assert "[DEEP_PLANNING_CONTEXT]" in prompt
                    assert "Test requirement" in prompt
                    assert "Test criteria" in prompt
                    assert "Test risk" in prompt
                    assert "Test strategy" in prompt

    def test_semantic_validation_integration(self, temp_workspace):
        """Test semantic validation integration with ready-to-submit logic"""
        with patch('executive_worker.agent.LLMClient') as mock_llm_class:
            mock_llm = Mock()
            mock_llm_class.return_value = mock_llm
            
            agent = ExecutiveWorker(temp_workspace, use_enhanced=False)
            agent.code.workspace_summary = Mock(return_value="workspace summary")
            
            ticket = Ticket("test", "Test", "Test description", None)
            deep_plan = DeepPlan(["req"], ["criteria"], ["risk"], "strategy", "medium")
            
            # Test case 1: Compilation fails
            validation = ValidationResult(compiled=False, tests=None)
            ready = agent.check_ready_to_submit(ticket, validation, deep_plan)
            assert ready == False
            
            # Test case 2: Tests fail
            validation = ValidationResult(compiled=True, tests=TestsSummary(passed=False, summary="failed"))
            ready = agent.check_ready_to_submit(ticket, validation, deep_plan)
            assert ready == False
            
            # Test case 3: Semantic validation fails
            validation = ValidationResult(compiled=True, tests=TestsSummary(passed=True, summary="ok"))
            
            # Mock semantic validation failure
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = '{"completed": false, "reason": "Not done"}'
            mock_llm.client.chat.completions.create.return_value = mock_response
            
            ready = agent.check_ready_to_submit(ticket, validation, deep_plan)
            assert ready == False
            
            # Test case 4: Everything passes
            mock_response.choices[0].message.content = '{"completed": true, "reason": "All done"}'
            ready = agent.check_ready_to_submit(ticket, validation, deep_plan)
            assert ready == True

    def test_error_recovery_integration(self, temp_workspace):
        """Test error recovery integration in plan execution"""
        with patch('executive_worker.agent.LLMClient') as mock_llm_class:
            mock_llm = Mock()
            mock_llm_class.return_value = mock_llm
            
            agent = ExecutiveWorker(temp_workspace, use_enhanced=True)
            
            # Mock shell to fail then succeed
            from executive_worker.models import CommandResult
            agent.shell.run = Mock(side_effect=[
                CommandResult("failing_cmd", 1, "", "Permission denied", 100),
                CommandResult("sudo failing_cmd", 0, "success", "", 50)
            ])
            
            # Test error recovery
            result = agent._execute_shell_with_recovery("failing_cmd", max_attempts=3)
            
            # Should have recovered successfully
            assert result.exit_code == 0
            assert "sudo" in result.cmd
            assert agent.shell.run.call_count == 2

    def test_task_tree_integration_with_deep_plan(self, temp_workspace):
        """Test task tree creation with deep planning context"""
        from executive_worker.task_tree import TaskTree
        
        deep_plan = DeepPlan(["req1", "req2"], ["criteria"], ["risk"], "strategy", "high")
        
        task_tree = TaskTree.load_or_create(temp_workspace, "test-ticket", "Test Ticket", deep_plan)
        
        # Should have created task tree with deep planning context
        assert task_tree.id == "test-ticket"
        assert task_tree.title == "Test Ticket"
        assert len(task_tree.nodes) >= 1
        
        # Should have node with deep planning context
        node = task_tree.nodes[0]
        assert "deep planning" in node.notes.lower()

    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'})
    def test_enhanced_mode_integration(self, temp_workspace):
        """Test Phase II features work with enhanced mode enabled"""
        agent = ExecutiveWorker(temp_workspace, use_enhanced=True)
        
        # Should have enhanced components
        assert agent.enhanced_code is not None
        assert agent.enhanced_edit_engine is not None
        assert agent.error_handler is not None
        
        # Test that enhanced mode is used in deep planning
        with patch.object(agent.enhanced_code, 'workspace_summary', return_value="enhanced summary") as mock_summary:
            with patch.object(agent.llm, 'analyze_requirements', return_value=["req"]):
                with patch.object(agent.llm, 'define_success_criteria', return_value=["criteria"]):
                    with patch.object(agent.llm, 'assess_complexity_and_risks', return_value=["risk"]):
                        with patch.object(agent.llm, 'create_strategy', return_value="strategy"):
                            
                            ticket = Ticket("test", "Test", "Test description", None)
                            deep_plan = agent.analyze_requirements_and_plan(ticket)
                            
                            # Should have used enhanced workspace summary
                            mock_summary.assert_called_once()
                            assert deep_plan.requirements == ["req"]
