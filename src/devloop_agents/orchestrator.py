from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime

from .adapters.github import GitHubTracker
from .adapters.local import LocalTracker
from .config import AppConfig
from .events import EventStore
from .models import AgentResult, Event, Role
from .probes import execute_probe
from .prompts import render_prompt
from .runner import AgentRunner, RunnerError
from .state import LeaseBusy, StateStore


class BudgetExceeded(RuntimeError):
    pass


class Orchestrator:
    def __init__(self, config: AppConfig):
        self.config = config
        self.events = EventStore(config.storage.events_path)
        self.state = StateStore(config.storage.state_path)
        if config.tracker.provider == "local":
            self.tracker = LocalTracker(config.tracker)
        elif config.tracker.provider == "github":
            self.tracker = GitHubTracker(config.tracker)
        else:
            raise ValueError(f"Unsupported tracker provider: {config.tracker.provider}")
        self.runner = AgentRunner(config.runner, config.project.workspace)

    def _emit(self, event: Event) -> None:
        self.events.append(event)
        print(f"[{event.role}] {event.message}", flush=True)

    def _check_budget(self) -> None:
        month = datetime.now(UTC).strftime("%Y-%m")
        total = 0.0
        for event in self.events.read(limit=10000):
            if str(event.get("timestamp", "")).startswith(month):
                cost = event.get("data", {}).get("cost_usd")
                if isinstance(cost, (int, float)):
                    total += float(cost)
        if total >= self.config.budget.monthly_usd:
            raise BudgetExceeded(
                f"Monthly agent budget reached (${total:.2f}/${self.config.budget.monthly_usd:.2f})"
            )

    def run_cycle(self, role: Role, apply: bool = False) -> int:
        if role == "monitor":
            return self._run_monitor(apply)
        self._check_budget()
        write_enabled = apply and self.config.runner.provider != "dry-run"
        run_id = uuid.uuid4().hex[:12]
        self._emit(Event("cycle.started", role, f"Cycle {run_id} started", run_id))
        items = self.tracker.queue(role, self.config.pipeline.max_items_per_cycle)
        if not items:
            self._emit(Event("cycle.empty", role, "No queued work items", run_id))
            return 0
        failures = 0
        for item in items:
            try:
                with self.state.lease(
                    f"{role}:{item.id}", run_id, self.config.runner.timeout_seconds + 300
                ):
                    self._emit(
                        Event("item.claimed", role, f"Claimed #{item.id}: {item.title}", run_id, item.id)
                    )
                    if write_enabled:
                        self.tracker.claim(role, item)
                    result = self.runner.run(role, item, render_prompt(role, item, self.config), apply)
                    if result.status in {"failed", "blocked", "skipped"}:
                        failures += 1
                        if write_enabled:
                            self.tracker.fail(role, item, result)
                    elif write_enabled:
                        self.tracker.complete(role, item, result)
                    self._emit(
                        Event(
                            "item.finished",
                            role,
                            result.summary,
                            run_id,
                            item.id,
                            "error" if result.status == "failed" else "info",
                            {
                                "status": result.status,
                                "pull_request_url": result.pull_request_url,
                                "cost_usd": result.cost_usd,
                                "turns": result.turns,
                            },
                        )
                    )
            except LeaseBusy as error:
                self._emit(Event("item.skipped", role, str(error), run_id, item.id, "warning"))
            except RunnerError as error:
                failures += 1
                result = AgentResult("failed", str(error))
                if write_enabled:
                    self.tracker.fail(role, item, result)
                self._emit(Event("item.failed", role, str(error), run_id, item.id, "error"))
        self._emit(Event("cycle.finished", role, f"Cycle finished with {failures} failure(s)", run_id))
        return 1 if failures else 0

    def _run_monitor(self, apply: bool) -> int:
        run_id = uuid.uuid4().hex[:12]
        self._emit(Event("cycle.started", "monitor", f"Cycle {run_id} started", run_id))
        failures = 0
        for probe in self.config.probes:
            result = execute_probe(probe, self.config.project.workspace)
            if result.healthy:
                self._emit(Event("probe.healthy", "monitor", f"{result.name}: {result.summary}", run_id))
                continue
            failures += 1
            message = f"{result.name}: {result.summary}"
            self._emit(Event("probe.failed", "monitor", message, run_id, level="error"))
            if apply:
                self.tracker.report_incident(
                    f"[{result.severity.upper()}] {result.name} health check failed",
                    f"DevLoop monitor detected a failed probe.\n\n{result.summary}",
                    result.fingerprint,
                )
        self._emit(
            Event("cycle.finished", "monitor", f"Checked {len(self.config.probes)} probe(s)", run_id)
        )
        return 1 if failures else 0

    def loop(self, role: Role, apply: bool = False) -> None:
        while True:
            self.run_cycle(role, apply)
            time.sleep(self.config.pipeline.poll_interval_seconds)
