from executive_worker.shell_runner import ShellRunner


def test_shell_runner_success_echo(tmp_path):
    runner = ShellRunner(cwd=str(tmp_path))
    result = runner.run("echo hello")
    assert result.success is True
    assert result.exit_code == 0
    assert "hello" in result.stdout


def test_shell_runner_failure_command(tmp_path):
    runner = ShellRunner(cwd=str(tmp_path))
    result = runner.run("bash -c 'exit 2'")
    assert result.success is False
    assert result.exit_code == 2

