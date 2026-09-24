from __future__ import annotations

import os
import shutil
import subprocess

from .config import AppConfig


def run_doctor(config: AppConfig) -> int:
    checks: list[tuple[str, bool | None, str]] = []
    checks.append(("workspace", config.project.workspace.is_dir(), str(config.project.workspace)))
    git_repo = (config.project.workspace / ".git").exists()
    checks.append(("git repository", git_repo if config.runner.provider == "command" else None, "optional in dry-run mode"))
    if config.tracker.provider == "github":
        token_set = bool(os.environ.get(config.tracker.token_env))
        checks.append(("GitHub token", token_set, config.tracker.token_env))
    else:
        checks.append(("local tracker", config.tracker.data_file.exists(), str(config.tracker.data_file)))
    if config.runner.provider == "command":
        executable = config.runner.command[0]
        checks.append(("agent command", shutil.which(executable) is not None, executable))
    else:
        checks.append(("agent runner", True, "dry-run provider"))
    try:
        completed = subprocess.run(
            ["git", "status", "--porcelain"], cwd=config.project.workspace, capture_output=True, timeout=5
        )
        checks.append(("git command", completed.returncode == 0, "available"))
    except (FileNotFoundError, subprocess.TimeoutExpired):
        checks.append(("git command", False, "unavailable"))

    for name, ok, detail in checks:
        status = "SKIP" if ok is None else "PASS" if ok else "FAIL"
        print(f"{status:4}  {name:18} {detail}")
    return 0 if all(ok is not False for _, ok, _ in checks) else 1
