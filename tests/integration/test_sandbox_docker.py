"""Integration tests for Docker Code Sandbox and Security Containment (TRD Section 20, Section 23, ADR-008, Test Plan Section 8)."""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.sandbox.docker_runner import DockerRunner, ServiceUnavailableError, get_docker_runner
from backend.app.sandbox.sandbox_spec import SandboxSpec
from backend.app.tools.base import ToolContext, ToolError
from backend.app.tools.code_tools import ExecuteCodeTool, RunTestsTool
from backend.app.tools.tool_registry import ToolRegistry


@pytest.fixture(scope="module")
def docker_runner():
    runner = DockerRunner()
    if not runner.is_available():
        pytest.skip("Docker engine is not running on this host environment")
    return runner


def test_valid_code_execution_in_docker(docker_runner, tmp_path):
    """Verify execution of valid Python code inside sovereign-sandbox container."""
    ws = tmp_path / "task_calc"
    spec = SandboxSpec(
        task_id="task_calc",
        code="result = sum(range(1, 11))\nprint(f'SUM={result}')",
        timeout_s=15,
        workspace_dir=ws,
    )

    res = docker_runner.run(spec)
    assert res.exit_code == 0
    assert "SUM=55" in res.stdout
    assert res.timed_out is False
    assert res.duration_ms > 0


def test_test_runner_command_execution(docker_runner, tmp_path):
    """Verify executing pytest test suite inside sandbox container."""
    ws = tmp_path / "task_pytest"
    ws.mkdir(parents=True, exist_ok=True)
    
    # Write code and test files in workspace
    (ws / "math_lib.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (ws / "test_math.py").write_text(
        "from math_lib import add\n\ndef test_add():\n    assert add(2, 3) == 5\n",
        encoding="utf-8",
    )

    spec = SandboxSpec(
        task_id="task_pytest",
        test_command="pytest test_math.py",
        timeout_s=15,
        workspace_dir=ws,
    )

    res = docker_runner.run(spec)
    assert res.exit_code == 0
    assert "1 passed" in res.stdout
    assert res.passed is True


def test_network_isolation_security_block(docker_runner, tmp_path):
    """Verify --network none blocks outbound socket/HTTP connections (TRD Section 23, Test Plan P30)."""
    ws = tmp_path / "task_net"
    code = """import urllib.request, socket
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2.0)
    s.connect(('8.8.8.8', 53))
    print('NETWORK_SUCCESS')
except Exception as e:
    print(f'NETWORK_BLOCKED: {type(e).__name__}')
"""
    spec = SandboxSpec(
        task_id="task_net",
        code=code,
        timeout_s=10,
        workspace_dir=ws,
    )

    res = docker_runner.run(spec)
    assert "NETWORK_SUCCESS" not in res.stdout
    assert "NETWORK_BLOCKED" in res.stdout


def test_timeout_enforced_sigkill(docker_runner, tmp_path):
    """Verify wrapper-enforced timeout terminates hanging infinite loops (TRD Section 23, Test Plan P33)."""
    ws = tmp_path / "task_timeout"
    code = "import time\nprint('STARTING_LOOP')\nwhile True:\n    time.sleep(0.1)\n"
    spec = SandboxSpec(
        task_id="task_timeout",
        code=code,
        timeout_s=2,
        workspace_dir=ws,
    )

    res = docker_runner.run(spec)
    assert res.timed_out is True
    assert res.exit_code == 124


def test_memory_limit_oom_exit_code(docker_runner, tmp_path):
    """Verify --memory=512m terminates OOM scripts with exit_code 137 (TRD Section 23, Test Plan P32)."""
    ws = tmp_path / "task_oom"
    # Attempt to allocate 1 GB of memory in chunks
    code = """
import sys
chunks = []
try:
    for _ in range(100):
        chunks.append(b'x' * (20 * 1024 * 1024))
    print('OOM_FAILED_ALLOCATED')
except MemoryError:
    print('CAUGHT_MEMORY_ERROR')
    sys.exit(137)
"""
    spec = SandboxSpec(
        task_id="task_oom",
        code=code,
        timeout_s=15,
        workspace_dir=ws,
    )

    res = docker_runner.run(spec)
    # The container will either be OOM-killed (137) or Python raises MemoryError (137)
    assert res.exit_code == 137
    assert "OOM_FAILED_ALLOCATED" not in res.stdout


def test_read_only_root_filesystem_security(docker_runner, tmp_path):
    """Verify --read-only prevents writes to container system directories (TRD Section 23, Test Plan P31)."""
    ws = tmp_path / "task_readonly"
    code = """
try:
    with open('/etc/hacked.txt', 'w') as f:
        f.write('pwned')
    print('WRITE_SUCCESS')
except OSError as e:
    print(f'WRITE_BLOCKED: {e}')
"""
    spec = SandboxSpec(
        task_id="task_readonly",
        code=code,
        timeout_s=10,
        workspace_dir=ws,
    )

    res = docker_runner.run(spec)
    assert "WRITE_SUCCESS" not in res.stdout
    assert "WRITE_BLOCKED" in res.stdout


def test_api_code_execute_endpoint(docker_runner):
    """Verify POST /api/code/execute endpoint (TRD Section 9, Table 17)."""
    client = TestClient(app)
    payload = {
        "language": "python",
        "code": "print('API_EXECUTE_OK')",
        "timeout_s": 15,
    }

    response = client.post("/api/code/execute", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["exit_code"] == 0
    assert "API_EXECUTE_OK" in data["stdout"]
    assert data["timed_out"] is False
    assert data["duration_ms"] > 0


def test_api_code_execute_unsupported_language_returns_422():
    """Verify POST /api/code/execute returns 422 for unsupported languages."""
    client = TestClient(app)
    response = client.post("/api/code/execute", json={"language": "javascript", "code": "console.log(1)"})
    assert response.status_code == 422


def test_docker_unavailable_negative_behavior_no_host_execution(monkeypatch):
    """Verify 503 / ToolError returned and ZERO host execution when Docker is down (TRD Table 51)."""
    # Simulate Docker daemon failure
    mock_runner = DockerRunner()
    monkeypatch.setattr(mock_runner, "is_available", lambda: False)

    spec = SandboxSpec(task_id="task_down", code="print('SHOULD_NEVER_RUN')")
    with pytest.raises(ServiceUnavailableError):
        mock_runner.run(spec)

    # Verify tool level behavior
    exec_tool = ExecuteCodeTool(runner=mock_runner)
    ctx = ToolContext(task_id="task_down", task_type="coding")
    with pytest.raises(ToolError) as exc_info:
        exec_tool.execute(exec_tool.metadata.input_schema(code="print('SHOULD_NEVER_RUN')"), ctx)
    assert "503 ServiceUnavailable" in str(exc_info.value)
