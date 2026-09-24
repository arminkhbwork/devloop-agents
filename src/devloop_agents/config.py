from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    pass


@dataclass(slots=True)
class ProjectConfig:
    name: str
    workspace: Path
    default_branch: str = "main"
    target_url: str = ""


@dataclass(slots=True)
class TrackerConfig:
    provider: str = "local"
    repository: str = ""
    token_env: str = "GITHUB_TOKEN"
    data_file: Path = Path(".devloop/issues.json")
    publish_agent_output: bool = False
    labels: dict[str, dict[str, str]] = field(default_factory=dict)


@dataclass(slots=True)
class RunnerConfig:
    provider: str = "dry-run"
    command: list[str] = field(default_factory=list)
    timeout_seconds: int = 1800
    pass_env: list[str] = field(default_factory=lambda: ["PATH", "LANG", "LC_ALL", "TMPDIR"])
    environment: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class PipelineConfig:
    poll_interval_seconds: int = 60
    max_items_per_cycle: int = 1
    require_human_review: bool = True
    allow_merge: bool = False
    allow_deploy: bool = False


@dataclass(slots=True)
class StorageConfig:
    state_path: Path = Path(".devloop/state.db")
    events_path: Path = Path(".devloop/events.jsonl")
    artifacts_path: Path = Path(".devloop/artifacts")


@dataclass(slots=True)
class BudgetConfig:
    monthly_usd: float = 50.0
    warn_at_percent: float = 80.0


@dataclass(slots=True)
class ProbeConfig:
    name: str
    kind: str
    target: str
    expected_status: int = 200
    timeout_seconds: int = 10
    severity: str = "high"


@dataclass(slots=True)
class AppConfig:
    path: Path
    project: ProjectConfig
    tracker: TrackerConfig
    runner: RunnerConfig
    pipeline: PipelineConfig
    storage: StorageConfig
    budget: BudgetConfig
    probes: list[ProbeConfig]


DEFAULT_LABELS: dict[str, dict[str, str]] = {
    "coder": {
        "queued": "agent:code",
        "claimed": "agent:in-progress",
        "completed": "agent:review",
        "blocked": "agent:blocked",
    },
    "qa": {
        "queued": "agent:qa",
        "claimed": "agent:qa-running",
        "completed": "agent:verified",
        "blocked": "agent:changes-requested",
    },
    "monitor": {
        "incident": "agent:incident",
        "managed": "agent:monitor",
    },
}


def _path(value: str | Path, base: Path) -> Path:
    path = Path(os.path.expandvars(os.path.expanduser(str(value))))
    return path if path.is_absolute() else (base / path).resolve()


def _table(raw: dict[str, Any], name: str) -> dict[str, Any]:
    value = raw.get(name, {})
    if not isinstance(value, dict):
        raise ConfigError(f"[{name}] must be a TOML table")
    return value


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path).expanduser().resolve()
    if not config_path.exists():
        raise ConfigError(f"Configuration file not found: {config_path}")
    with config_path.open("rb") as handle:
        raw = tomllib.load(handle)
    base = config_path.parent

    project_raw = _table(raw, "project")
    if not project_raw.get("name"):
        raise ConfigError("[project].name is required")
    project = ProjectConfig(
        name=str(project_raw["name"]),
        workspace=_path(project_raw.get("workspace", "."), base),
        default_branch=str(project_raw.get("default_branch", "main")),
        target_url=str(project_raw.get("target_url", "")),
    )

    tracker_raw = _table(raw, "tracker")
    labels = {role: values.copy() for role, values in DEFAULT_LABELS.items()}
    for role, values in tracker_raw.get("labels", {}).items():
        if isinstance(values, dict):
            labels.setdefault(role, {}).update({str(k): str(v) for k, v in values.items()})
    tracker = TrackerConfig(
        provider=str(tracker_raw.get("provider", "local")),
        repository=str(tracker_raw.get("repository", "")),
        token_env=str(tracker_raw.get("token_env", "GITHUB_TOKEN")),
        data_file=_path(tracker_raw.get("data_file", ".devloop/issues.json"), base),
        publish_agent_output=bool(tracker_raw.get("publish_agent_output", False)),
        labels=labels,
    )

    runner_raw = _table(raw, "runner")
    command = runner_raw.get("command", [])
    if not isinstance(command, list) or not all(isinstance(value, str) for value in command):
        raise ConfigError("[runner].command must be an array of strings")
    pass_env = runner_raw.get("pass_env", ["PATH", "LANG", "LC_ALL", "TMPDIR"])
    if not isinstance(pass_env, list) or not all(isinstance(value, str) for value in pass_env):
        raise ConfigError("[runner].pass_env must be an array of environment-variable names")
    runner = RunnerConfig(
        provider=str(runner_raw.get("provider", "dry-run")),
        command=command,
        timeout_seconds=int(runner_raw.get("timeout_seconds", 1800)),
        pass_env=pass_env,
        environment={str(k): str(v) for k, v in runner_raw.get("environment", {}).items()},
    )

    pipeline_raw = _table(raw, "pipeline")
    pipeline = PipelineConfig(
        poll_interval_seconds=int(pipeline_raw.get("poll_interval_seconds", 60)),
        max_items_per_cycle=int(pipeline_raw.get("max_items_per_cycle", 1)),
        require_human_review=bool(pipeline_raw.get("require_human_review", True)),
        allow_merge=bool(pipeline_raw.get("allow_merge", False)),
        allow_deploy=bool(pipeline_raw.get("allow_deploy", False)),
    )
    if pipeline.allow_merge or pipeline.allow_deploy:
        raise ConfigError("Public safety policy forbids automatic merge and deployment")

    storage_raw = _table(raw, "storage")
    storage = StorageConfig(
        state_path=_path(storage_raw.get("state_path", ".devloop/state.db"), base),
        events_path=_path(storage_raw.get("events_path", ".devloop/events.jsonl"), base),
        artifacts_path=_path(storage_raw.get("artifacts_path", ".devloop/artifacts"), base),
    )
    budget_raw = _table(raw, "budget")
    budget = BudgetConfig(
        monthly_usd=float(budget_raw.get("monthly_usd", 50.0)),
        warn_at_percent=float(budget_raw.get("warn_at_percent", 80.0)),
    )
    probes = [
        ProbeConfig(
            name=str(probe["name"]),
            kind=str(probe.get("kind", "http")),
            target=str(probe["target"]),
            expected_status=int(probe.get("expected_status", 200)),
            timeout_seconds=int(probe.get("timeout_seconds", 10)),
            severity=str(probe.get("severity", "high")),
        )
        for probe in raw.get("probes", [])
    ]
    if not project.workspace.exists():
        raise ConfigError(f"Project workspace does not exist: {project.workspace}")
    if tracker.provider == "github" and not tracker.repository:
        raise ConfigError("[tracker].repository is required for the GitHub provider")
    if runner.provider == "command" and not runner.command:
        raise ConfigError("[runner].command is required for the command provider")
    if tracker.token_env in runner.pass_env:
        raise ConfigError(f"[runner].pass_env cannot forward tracker credential {tracker.token_env}")
    if tracker.token_env in runner.environment:
        raise ConfigError(f"[runner].environment cannot define tracker credential {tracker.token_env}")
    tracker_reference = f"${{{tracker.token_env}}}"
    if any(tracker_reference in value for value in runner.environment.values()):
        raise ConfigError(f"[runner].environment cannot reference tracker credential {tracker.token_env}")
    return AppConfig(config_path, project, tracker, runner, pipeline, storage, budget, probes)
