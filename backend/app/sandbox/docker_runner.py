"""Docker Sandbox Runner (TRD Section 20, Section 23, ADR-008, Component #16).

Executes generated code and tests inside an isolated sovereign-sandbox container.
Strictly adheres to:
- --network none
- --read-only
- --cpus=1
- --memory=512m
- --pids-limit=64
- --user 1000:1000
- --security-opt=no-new-privileges:true
- --tmpfs /tmp:rw,noexec,nosuid,size=64m
- Volume bind-mounted task workspace only
- Zero host code execution fallback under all conditions.
"""

import logging
import os
from pathlib import Path
import shutil
import subprocess
import time
from typing import List, Optional

from backend.app.core.config import settings
from backend.app.sandbox.sandbox_spec import SandboxSpec, SandboxResult

logger = logging.getLogger("sovereign_workbench.sandbox")
security_logger = logging.getLogger("sovereign_workbench.security")


class ServiceUnavailableError(RuntimeError):
    """Raised when Docker daemon is not running or unreachable."""
    pass


class DockerRunner:
    """Orchestrates ephemeral Docker sandbox containers for code execution."""

    def __init__(
        self,
        image_name: Optional[str] = None,
        timeout_s: Optional[int] = None,
        cpu_limit: Optional[float] = None,
        memory_limit: Optional[str] = None,
        pids_limit: Optional[int] = None,
    ):
        self.image_name = image_name or settings.sandbox.image_name
        self.timeout_s = timeout_s or settings.sandbox.timeout_s
        self.cpu_limit = cpu_limit or settings.sandbox.cpu_limit
        self.memory_limit = memory_limit or settings.sandbox.memory_limit
        self.pids_limit = pids_limit or settings.sandbox.pids_limit
        self.max_output_bytes = settings.sandbox.max_output_bytes

    def is_available(self) -> bool:
        """Probe whether the local Docker engine is reachable."""
        try:
            res = subprocess.run(
                ["docker", "info"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
                check=False,
            )
            return res.returncode == 0
        except Exception:
            return False

    def _normalize_mount_path(self, path: Path) -> str:
        """Format host path for Docker volume mounting."""
        resolved = str(path.resolve())
        # Convert backslashes for Docker CLI compatibility
        return resolved.replace("\\", "/")

    def run(self, spec: SandboxSpec) -> SandboxResult:
        """Run code or test command inside an isolated Docker sandbox container."""
        # 1. Hard requirement: Docker daemon must be available
        if not self.is_available():
            logger.error("Docker daemon unavailable. Host execution fallback strictly forbidden (TRD Table 51).")
            raise ServiceUnavailableError("503 ServiceUnavailable: Docker daemon is not running or unreachable.")

        # 2. Resolve and prepare task workspace directory
        if spec.workspace_dir is not None:
            workspace_path = spec.workspace_dir.resolve()
        else:
            workspace_path = (Path(settings.paths.data_dir) / "sandbox" / spec.task_id).resolve()
        workspace_path.mkdir(parents=True, exist_ok=True)

        # 3. Write code file if provided
        if spec.code:
            code_file = workspace_path / "main.py"
            code_file.write_text(spec.code, encoding="utf-8")

        # 4. Construct container command
        if spec.test_command:
            container_cmd = ["sh", "-c", spec.test_command]
        else:
            container_cmd = ["python", "main.py"]

        mount_source = self._normalize_mount_path(workspace_path)
        effective_timeout = spec.timeout_s or self.timeout_s

        # 5. Assemble strict security flags per TRD §23 & ADR-008
        cmd: List[str] = [
            "docker", "run",
            "--rm",
            "--network", "none",
            f"--cpus={self.cpu_limit}",
            f"--memory={self.memory_limit}",
            f"--pids-limit={self.pids_limit}",
            "--read-only",
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
            "--security-opt", "no-new-privileges:true",
            "--user", "1000:1000",
            "--label", "app=sovereign-sandbox",
            "--label", f"task_id={spec.task_id}",
            "-v", f"{mount_source}:/workspace:rw",
            "-w", "/workspace",
            self.image_name,
        ] + container_cmd

        logger.info(
            f"Executing sandbox container for task '{spec.task_id}' with timeout {effective_timeout}s: "
            f"{' '.join(cmd[:6])} ... [image={self.image_name}]"
        )

        start_time = time.time()
        proc = None
        timed_out = False
        stdout_text = ""
        stderr_text = ""
        exit_code = 0

        try:
            # Execute container runner with sanitized minimal environment (no host secrets)
            clean_env = {
                "PATH": os.environ.get("PATH", ""),
                "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
            }
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False,
                env=clean_env,
            )
            raw_stdout, raw_stderr = proc.communicate(timeout=effective_timeout)
            exit_code = proc.returncode

            # Decode and enforce size limit
            stdout_text = raw_stdout[:self.max_output_bytes].decode("utf-8", errors="replace")
            stderr_text = raw_stderr[:self.max_output_bytes].decode("utf-8", errors="replace")

        except subprocess.TimeoutExpired:
            timed_out = True
            logger.warning(f"Sandbox container execution timed out after {effective_timeout}s for task '{spec.task_id}'")
            if proc:
                proc.kill()
                try:
                    raw_stdout, raw_stderr = proc.communicate(timeout=2)
                    stdout_text = raw_stdout[:self.max_output_bytes].decode("utf-8", errors="replace")
                    stderr_text = raw_stderr[:self.max_output_bytes].decode("utf-8", errors="replace")
                except Exception:
                    pass
            exit_code = 124  # Standard timeout exit code
            stderr_text += f"\n[Process killed: Execution timed out after {effective_timeout} seconds]"

        except Exception as e:
            logger.error(f"Error launching sandbox container: {e}", exc_info=True)
            raise ServiceUnavailableError(f"Failed to launch sandbox container: {e}") from e

        duration_ms = int((time.time() - start_time) * 1000)

        # Evaluate passed status if test command was given
        passed = (exit_code == 0) if spec.test_command is not None else None

        return SandboxResult(
            stdout=stdout_text,
            stderr=stderr_text,
            exit_code=exit_code,
            timed_out=timed_out,
            duration_ms=duration_ms,
            passed=passed,
        )


# Global singleton
_global_docker_runner: Optional[DockerRunner] = None


def get_docker_runner() -> DockerRunner:
    global _global_docker_runner
    if _global_docker_runner is None:
        _global_docker_runner = DockerRunner()
    return _global_docker_runner
