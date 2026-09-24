import json
import tempfile
import unittest
from unittest.mock import patch
import sys
from pathlib import Path

from devloop_agents.config import RunnerConfig
from devloop_agents.models import WorkItem
from devloop_agents.runner import AgentRunner


class RunnerTest(unittest.TestCase):
    def test_dry_run_never_executes_command(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runner = AgentRunner(RunnerConfig(provider="command", command=["missing-command"]), Path(directory))
            result = runner.run("coder", WorkItem("1", "Test"), "prompt", apply=False)
            self.assertEqual(result.status, "dry_run")

    def test_parses_structured_result(self) -> None:
        payload = {
            "status": "completed",
            "summary": "Opened PR",
            "pull_request_url": "https://github.com/example/repo/pull/1",
            "cost_usd": 0.12,
            "turns": 4,
        }
        result = AgentRunner._parse_result("notes\nDEVLOOP_RESULT: " + json.dumps(payload))
        self.assertEqual(result.summary, "Opened PR")
        self.assertEqual(result.cost_usd, 0.12)
        self.assertEqual(result.turns, 4)

    def test_child_does_not_inherit_tracker_token(self) -> None:
        script = (
            "import json,os; "
            "print('DEVLOOP_RESULT: '+json.dumps({'status':'completed',"
            "'summary':str(os.getenv(\"GITHUB_TOKEN\"))}))"
        )
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            "os.environ", {"GITHUB_TOKEN": "github-secret-value"}, clear=False
        ):
            runner = AgentRunner(
                RunnerConfig(provider="command", command=[sys.executable, "-c", script]),
                Path(directory),
            )
            result = runner.run("coder", WorkItem("1", "Test"), "prompt", apply=True)
            self.assertEqual(result.summary, "None")

    def test_explicit_agent_secret_is_redacted_from_output(self) -> None:
        script = (
            "import json,os; s=os.getenv('AGENT_API_KEY'); "
            "print('DEVLOOP_RESULT: '+json.dumps({'status':'completed','summary':s,'details':s}))"
        )
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            "os.environ", {"AGENT_API_KEY": "provider-secret-value"}, clear=False
        ):
            runner = AgentRunner(
                RunnerConfig(
                    provider="command",
                    command=[sys.executable, "-c", script],
                    pass_env=["PATH", "AGENT_API_KEY"],
                ),
                Path(directory),
            )
            result = runner.run("coder", WorkItem("1", "Test"), "prompt", apply=True)
            self.assertEqual(result.summary, "[REDACTED]")
            self.assertEqual(result.details, "[REDACTED]")


if __name__ == "__main__":
    unittest.main()
