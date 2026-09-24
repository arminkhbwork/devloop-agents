from __future__ import annotations

import argparse
import sys
from importlib.resources import files
from pathlib import Path

from .config import ConfigError, load_config
from .dashboard import serve_dashboard
from .doctor import run_doctor
from .models import Role
from .orchestrator import BudgetExceeded, Orchestrator


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="devloop", description="Portable coding, QA, and monitoring agents")
    root.add_argument("--config", default="devloop.toml", help="path to devloop.toml")
    commands = root.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init", help="create a safe starter configuration")
    init.add_argument("--force", action="store_true", help="replace an existing devloop.toml")

    doctor = commands.add_parser("doctor", help="validate configuration and integrations")
    doctor.set_defaults(action="doctor")

    run = commands.add_parser("run", help="run one role once or continuously")
    run.add_argument("role", choices=["coder", "qa", "monitor"])
    run.add_argument("--apply", action="store_true", help="allow tracker writes and execute the configured agent")
    run.add_argument("--loop", action="store_true", help="poll continuously")

    dashboard = commands.add_parser("dashboard", help="serve the local operations dashboard")
    dashboard.add_argument("--host", default="127.0.0.1")
    dashboard.add_argument("--port", default=8765, type=int)
    return root


def _init(config_path: Path, force: bool) -> int:
    if config_path.exists() and not force:
        print(f"Refusing to replace existing file: {config_path}", file=sys.stderr)
        return 1
    config_path.parent.mkdir(parents=True, exist_ok=True)
    source = files("devloop_agents").joinpath("templates", "devloop.example.toml")
    config_path.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"Created {config_path}. Run: devloop --config {config_path} doctor")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    config_path = Path(args.config).expanduser().resolve()
    if args.command == "init":
        return _init(config_path, args.force)
    try:
        config = load_config(config_path)
        if args.command == "doctor":
            return run_doctor(config)
        if args.command == "dashboard":
            serve_dashboard(config, args.host, args.port)
            return 0
        orchestrator = Orchestrator(config)
        if args.loop:
            orchestrator.loop(args.role, args.apply)
            return 0
        return orchestrator.run_cycle(args.role, args.apply)
    except (ConfigError, BudgetExceeded, ValueError) as error:
        print(f"devloop: {error}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
