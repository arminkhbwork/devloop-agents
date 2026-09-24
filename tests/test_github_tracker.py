import unittest

from devloop_agents.adapters.github import GitHubTracker
from devloop_agents.config import DEFAULT_LABELS, TrackerConfig
from devloop_agents.models import AgentResult, WorkItem


class GitHubTrackerOutputTest(unittest.TestCase):
    def tracker(self, publish: bool = False) -> GitHubTracker:
        tracker = GitHubTracker.__new__(GitHubTracker)
        tracker.config = TrackerConfig(
            repository="example/project",
            publish_agent_output=publish,
            labels=DEFAULT_LABELS,
        )
        tracker.token = "unused"
        return tracker

    def test_default_comment_does_not_publish_agent_text(self) -> None:
        tracker = self.tracker()
        captured = {}
        tracker._transition = lambda role, item, destination, comment: captured.update(comment=comment)
        tracker.complete(
            "coder",
            WorkItem("1", "Issue"),
            AgentResult(
                "completed",
                "secret model summary",
                details="secret raw output",
                pull_request_url="https://github.com/example/project/pull/42",
            ),
        )
        self.assertNotIn("secret model summary", captured["comment"])
        self.assertNotIn("secret raw output", captured["comment"])
        self.assertIn("https://github.com/example/project/pull/42", captured["comment"])

    def test_rejects_pull_request_url_for_another_repository(self) -> None:
        tracker = self.tracker()
        self.assertIsNone(tracker._safe_pull_request_url("https://github.com/other/repo/pull/1"))

    def test_agent_output_can_be_explicitly_enabled(self) -> None:
        tracker = self.tracker(publish=True)
        captured = {}
        tracker._transition = lambda role, item, destination, comment: captured.update(comment=comment)
        tracker.complete(
            "qa",
            WorkItem("1", "Issue"),
            AgentResult("completed", "2/2 checks passed", details="evidence"),
        )
        self.assertIn("2/2 checks passed", captured["comment"])
        self.assertIn("evidence", captured["comment"])


if __name__ == "__main__":
    unittest.main()
