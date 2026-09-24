from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from .config import RunnerConfig
from .events import redact_values
from .models import AgentResult, Role, WorkItem

RESULT_PREFIX = "DEVLOOP_RESULT:"


class RunnerError(RuntimeError):
    pass


class AgentRunner:
    def __init__(self, config: RunnerConfig, workspace: Path):
        self.config = config
        self.workspace = workspace

    def run(self, role: Role, item: WorkItem, prompt: str, apply: bool) -> AgentResult:
        if not apply or self.config.provider == "dry-run":
            return AgentResult(
                status="dry_run",
                summary=f"Dry run prepared for {role} item #{item.id}: {item.title}",
                details=prompt,
            )
        if self.config.provider != "command":
            raise RunnerError(f"Unsupported runner provider: {self.config.provider}")
        environment = {
            key: os.environ[key]
            for key in self.config.pass_env
            if key in os.environ
        }
        environment.update(
            {key: os.path.expandvars(value) for key, value in self.config.environment.items()}
        )
        secret_values = [
            value
            for key, value in os.environ.items()
            if any(marker in key.upper() for marker in ("TOKEN", "SECRET", "PASSWORD", "API_KEY"))
        ]
        secret_values.extend(
            value
            for key, value in environment.items()
            if any(marker in key.upper() for marker in ("TOKEN", "SECRET", "PASSWORD", "API_KEY"))
        )
        try:
            completed = subprocess.run(
                self.config.command,
                cwd=self.workspace,
                input=prompt,
                text=True,
                capture_output=True,
                timeout=self.config.timeout_seconds,
                env=environment,
                check=False,
            )
        except FileNotFoundError as error:
            raise RunnerError(f"Agent command not found: {self.config.command[0]}") from error
        except subprocess.TimeoutExpired as error:
            raise RunnerError(f"Agent exceeded {self.config.timeout_seconds}s timeout") from error

        output = redact_values(
            "\n".join(part for part in (completed.stdout, completed.stderr) if part).strip(),
            secret_values,
        )
        parsed = self._parse_result(output)
        if completed.returncode != 0 and parsed.status == "completed":
            parsed.status = "failed"
            parsed.summary = f"Agent command exited with status {completed.returncode}"
        if not parsed.details:
            parsed.details = output[-8000:]
        return parsed

    @staticmethod
    def _parse_result(output: str) -> AgentResult:
        for line in reversed(output.splitlines()):
            if not line.startswith(RESULT_PREFIX):
                continue
            try:
                payload = json.loads(line[len(RESULT_PREFIX) :].strip())
                status = payload.get("status", "completed")
                if status not in {"completed", "blocked", "failed", "skipped", "dry_run"}:
                    raise ValueError(f"Unknown agent result status: {status}")
                return AgentResult(
                    status=status,
                    summary=str(payload.get("summary", "Agent completed")),
                    details=str(payload.get("details", "")),
                    pull_request_url=payload.get("pull_request_url"),
                    cost_usd=float(payload["cost_usd"]) if payload.get("cost_usd") is not None else None,
                    turns=int(payload["turns"]) if payload.get("turns") is not None else None,
                    metadata=dict(payload.get("metadata", {})),
                )
            except (TypeError, ValueError, json.JSONDecodeError):
                break
        return AgentResult(status="completed", summary="Agent completed without a structured result", details=output)
