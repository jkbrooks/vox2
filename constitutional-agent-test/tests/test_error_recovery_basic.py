import pytest
import tempfile
from unittest.mock import Mock, patch
from executive_worker.agent import ExecutiveWorker
from executive_worker.models import CommandResult


class TestErrorRecovery:
    
    @pytest.fixture
    def agent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('executive_worker.agent.LLMClient') as mock_llm:
                mock_llm.return_value.model = "gpt-4o-mini"
                agent = ExecutiveWorker(tmpdir, use_enhanced=True)
                return agent

    def test_execute_shell_with_recovery_success_first_try(self, agent):
        success_result = CommandResult("echo hello", 0, "hello\n", "", 10)
        agent.shell.run = Mock(return_value=success_result)
        
        result = agent._execute_shell_with_recovery("echo hello", max_attempts=5)
        
        assert result.exit_code == 0
        agent.shell.run.assert_called_once_with("echo hello")

    def test_apply_fallback_recovery_permission_denied(self, agent):
        failed_result = CommandResult("mkdir /protected", 1, "", "Permission denied", 10)
        
        recovered_cmd = agent._apply_fallback_recovery("mkdir /protected", failed_result, 0)
        
        assert recovered_cmd == "sudo mkdir /protected"

    def test_apply_fallback_recovery_cargo_clean(self, agent):
        failed_result = CommandResult("cargo check", 101, "", "error: failed to compile", 2000)
        
        recovered_cmd = agent._apply_fallback_recovery("cargo check", failed_result, 0)
        assert recovered_cmd == "cargo clean && cargo check"
