import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass

from executive_worker.agent import ExecutiveWorker
from executive_worker.models import Ticket, DeepPlan
from executive_worker.llm_client import LLMClient


class TestDeepPlanningAnalysis:
    """Test suite for Phase II deep planning functionality"""
    
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
            description="Create a sophisticated event-driven system with custom derive macros, async processing, and ECS integration.",
            eoi=None
        )

    def test_analyze_requirements_extraction(self, agent, sample_ticket, mock_llm_client):
        """Test that requirements are properly extracted from ticket description"""
        # Mock LLM response for requirement analysis
        mock_llm_client.analyze_requirements.return_value = [
            "Create async event system with EventBus",
            "Implement custom derive macro for Event trait",
            "Add ECS integration components"
        ]
        
        mock_llm_client.define_success_criteria.return_value = [
            "cargo check passes",
            "all tests pass", 
            "event system handles 1000+ events/sec"
        ]
        
        mock_llm_client.assess_complexity_and_risks.return_value = [
            "Async runtime integration complexity",
            "Macro syntax edge cases"
        ]
        
        mock_llm_client.create_strategy.return_value = "Implement core event types first, then async processing, finally ECS integration"
        
        # Execute deep planning
        deep_plan = agent.analyze_requirements_and_plan(sample_ticket)
        
        # Verify deep plan structure
        assert isinstance(deep_plan, DeepPlan)
        assert len(deep_plan.requirements) == 3
        assert "async event system" in deep_plan.requirements[0].lower()
        assert len(deep_plan.success_criteria) == 3
        assert "cargo check passes" in deep_plan.success_criteria
        assert len(deep_plan.risks) == 2
        assert "async runtime" in deep_plan.risks[0].lower()
        assert deep_plan.strategy != ""
        assert deep_plan.estimated_complexity in ["low", "medium", "high", "epic"]
        
        # Verify LLM was called with correct parameters
        mock_llm_client.analyze_requirements.assert_called_once_with(sample_ticket.description)
        mock_llm_client.define_success_criteria.assert_called_once()
        mock_llm_client.assess_complexity_and_risks.assert_called_once()
        mock_llm_client.create_strategy.assert_called_once()

    def test_complexity_estimation_logic(self, agent, sample_ticket, mock_llm_client):
        """Test complexity estimation based on requirements and risks"""
        # Test low complexity (few requirements, no risky keywords)
        mock_llm_client.analyze_requirements.return_value = ["Simple task", "Basic implementation"]
        mock_llm_client.define_success_criteria.return_value = ["Works correctly"]
        mock_llm_client.assess_complexity_and_risks.return_value = ["Minor risk"]
        mock_llm_client.create_strategy.return_value = "Simple approach"
        
        deep_plan = agent.analyze_requirements_and_plan(sample_ticket)
        assert deep_plan.estimated_complexity == "low"
        
        # Test high complexity (many requirements with async/macro keywords)
        mock_llm_client.analyze_requirements.return_value = [
            "Async event system", "Custom derive macro", "Complex integration",
            "Performance optimization", "Error handling", "Testing framework",
            "Documentation", "Benchmarking", "Monitoring", "Deployment", "More stuff"
        ]
        mock_llm_client.assess_complexity_and_risks.return_value = [
            "Async runtime complexity", "Macro edge cases", "Integration issues", "Performance bottlenecks"
        ]
        
        deep_plan = agent.analyze_requirements_and_plan(sample_ticket)
        assert deep_plan.estimated_complexity == "high"
        
        # Test epic complexity (very many requirements)
        mock_llm_client.analyze_requirements.return_value = [f"Requirement {i}" for i in range(20)]
        
        deep_plan = agent.analyze_requirements_and_plan(sample_ticket)
        assert deep_plan.estimated_complexity == "epic"

    def test_llm_requirement_analysis_methods(self, temp_workspace):
        """Test LLM client requirement analysis methods"""
        llm_client = LLMClient()
        
        # Mock OpenAI client
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '["Create event system", "Add async processing"]'
        
        with patch.object(llm_client.client.chat.completions, 'create', return_value=mock_response):
            requirements = llm_client.analyze_requirements("Build an event system with async processing")
            
            assert isinstance(requirements, list)
            assert len(requirements) == 2
            assert "event system" in requirements[0].lower()
            assert "async processing" in requirements[1].lower()

    def test_fallback_requirement_parsing(self, temp_workspace):
        """Test fallback requirement parsing when LLM fails"""
        llm_client = LLMClient()
        
        # Mock LLM failure
        with patch.object(llm_client.client.chat.completions, 'create', side_effect=Exception("API Error")):
            description = """
            Please create a new async event system.
            Implement custom derive macros for the Event trait.
            Add comprehensive testing.
            Build integration with ECS components.
            """
            requirements = llm_client.analyze_requirements(description)
            
            # Should fallback to heuristic parsing
            assert isinstance(requirements, list)
            assert len(requirements) > 0
            # Should find lines with action keywords
            create_found = any("create" in req.lower() for req in requirements)
            implement_found = any("implement" in req.lower() for req in requirements)
            assert create_found or implement_found

    def test_success_criteria_generation(self, temp_workspace):
        """Test success criteria generation"""
        llm_client = LLMClient()
        ticket = Ticket("test", "Test Ticket", "Build something", None)
        requirements = ["Build feature X", "Add tests"]
        
        # Mock successful response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '["Feature X works correctly", "All tests pass", "Performance meets requirements"]'
        
        with patch.object(llm_client.client.chat.completions, 'create', return_value=mock_response):
            criteria = llm_client.define_success_criteria(ticket, requirements)
            
            assert isinstance(criteria, list)
            assert len(criteria) == 3
            assert any("tests pass" in c.lower() for c in criteria)

    def test_success_criteria_fallback(self, temp_workspace):
        """Test success criteria fallback when LLM fails"""
        llm_client = LLMClient()
        ticket = Ticket("test", "Test Ticket", "Build something", None)
        requirements = ["Build feature"]
        
        # Mock LLM failure
        with patch.object(llm_client.client.chat.completions, 'create', side_effect=Exception("API Error")):
            criteria = llm_client.define_success_criteria(ticket, requirements)
            
            # Should return fallback criteria
            assert isinstance(criteria, list)
            assert len(criteria) == 4
            assert any("compiles" in c.lower() for c in criteria)
            assert any("tests pass" in c.lower() for c in criteria)

    def test_risk_assessment(self, temp_workspace):
        """Test complexity and risk assessment"""
        llm_client = LLMClient()
        ticket = Ticket("test", "Async System", "Build async event system with macros", None)
        requirements = ["Async processing", "Custom macros"]
        codebase_summary = "Rust project with basic structure"
        
        # Mock successful response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '["Async runtime complexity", "Macro compilation issues", "Integration challenges"]'
        
        with patch.object(llm_client.client.chat.completions, 'create', return_value=mock_response):
            risks = llm_client.assess_complexity_and_risks(ticket, requirements, codebase_summary)
            
            assert isinstance(risks, list)
            assert len(risks) == 3
            assert any("async" in r.lower() for r in risks)
            assert any("macro" in r.lower() for r in risks)

    def test_risk_assessment_fallback(self, temp_workspace):
        """Test risk assessment fallback logic"""
        llm_client = LLMClient()
        ticket = Ticket("test", "Async Macro System", "Build async system with custom derive macros", None)
        requirements = ["Async processing"]
        
        # Mock LLM failure
        with patch.object(llm_client.client.chat.completions, 'create', side_effect=Exception("API Error")):
            risks = llm_client.assess_complexity_and_risks(ticket, requirements, "codebase")
            
            # Should identify risks from keywords
            assert isinstance(risks, list)
            assert len(risks) > 0
            # Should find async and macro related risks
            async_risk_found = any("async" in r.lower() for r in risks)
            macro_risk_found = any("macro" in r.lower() for r in risks)
            assert async_risk_found or macro_risk_found

    def test_strategy_creation(self, temp_workspace):
        """Test strategy creation"""
        llm_client = LLMClient()
        ticket = Ticket("test", "Event System", "Build event system", None)
        requirements = ["Core events", "Async processing"]
        risks = ["Complexity"]
        codebase_summary = "Rust project"
        
        # Mock successful response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Start with core event types, then add async processing, finally integrate with existing systems."
        
        with patch.object(llm_client.client.chat.completions, 'create', return_value=mock_response):
            strategy = llm_client.create_strategy(ticket, requirements, risks, codebase_summary)
            
            assert isinstance(strategy, str)
            assert len(strategy) > 10
            assert "event" in strategy.lower()

    def test_strategy_creation_fallback(self, temp_workspace):
        """Test strategy creation fallback"""
        llm_client = LLMClient()
        ticket = Ticket("test", "System", "Build system", None)
        requirements = []
        risks = []
        
        # Mock LLM failure
        with patch.object(llm_client.client.chat.completions, 'create', side_effect=Exception("API Error")):
            strategy = llm_client.create_strategy(ticket, requirements, risks, "codebase")
            
            # Should return fallback strategy
            assert isinstance(strategy, str)
            assert "incremental" in strategy.lower()

    def test_deep_plan_integration_with_task_tree(self, agent, sample_ticket, mock_llm_client):
        """Test that deep plan is properly integrated with task tree creation"""
        # Mock deep planning responses
        mock_llm_client.analyze_requirements.return_value = ["Req 1", "Req 2"]
        mock_llm_client.define_success_criteria.return_value = ["Criteria 1"]
        mock_llm_client.assess_complexity_and_risks.return_value = ["Risk 1"]
        mock_llm_client.create_strategy.return_value = "Strategy"
        
        # Mock codebase utilities
        agent.code.workspace_summary = Mock(return_value="Mock workspace summary")
        
        # Execute deep planning
        deep_plan = agent.analyze_requirements_and_plan(sample_ticket)
        
        # Test task tree creation with deep plan
        from executive_worker.task_tree import TaskTree
        task_tree = TaskTree.load_or_create(agent.workspace_root, sample_ticket.ticket_id, sample_ticket.title, deep_plan)
        
        # Verify task tree has been influenced by deep plan
        assert task_tree.id == sample_ticket.ticket_id
        assert task_tree.title == sample_ticket.title
        assert len(task_tree.nodes) >= 1  # Should have at least one node from deep planning
        
        # Check that the node has the deep planning context
        node = task_tree.nodes[0]
        assert "deep planning" in node.notes.lower()

    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'})
    def test_deep_planning_with_enhanced_mode(self, temp_workspace):
        """Test deep planning with enhanced codebase utilities"""
        # Create some test files
        os.makedirs(os.path.join(temp_workspace, "src"), exist_ok=True)
        with open(os.path.join(temp_workspace, "src", "main.rs"), "w") as f:
            f.write("fn main() { println!('Hello'); }")
        
        with patch('executive_worker.agent.LLMClient') as mock_llm_class:
            mock_llm = Mock()
            mock_llm.analyze_requirements.return_value = ["Test requirement"]
            mock_llm.define_success_criteria.return_value = ["Test passes"]
            mock_llm.assess_complexity_and_risks.return_value = ["Low risk"]
            mock_llm.create_strategy.return_value = "Simple strategy"
            mock_llm_class.return_value = mock_llm
            
            # Test with enhanced mode enabled
            agent = ExecutiveWorker(temp_workspace, use_enhanced=True)
            ticket = Ticket("test", "Test", "Test description", None)
            
            # Mock enhanced codebase utils
            if agent.enhanced_code:
                agent.enhanced_code.workspace_summary = Mock(return_value="Enhanced workspace summary")
            
            deep_plan = agent.analyze_requirements_and_plan(ticket)
            
            # Verify deep plan was created
            assert isinstance(deep_plan, DeepPlan)
            assert deep_plan.requirements == ["Test requirement"]
            assert deep_plan.success_criteria == ["Test passes"]
            assert deep_plan.risks == ["Low risk"]
            assert deep_plan.strategy == "Simple strategy"
