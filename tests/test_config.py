import tempfile
import unittest
from pathlib import Path

from devloop_agents.config import ConfigError, load_config


BASE = """
[project]
name = "Test"
workspace = "."

[tracker]
provider = "local"
data_file = "issues.json"

[runner]
provider = "dry-run"

[pipeline]
allow_merge = false
allow_deploy = false
"""


class ConfigTest(unittest.TestCase):
    def test_loads_minimal_config_and_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "devloop.toml"
            path.write_text(BASE, encoding="utf-8")
            config = load_config(path)
            self.assertEqual(config.project.name, "Test")
            self.assertEqual(config.tracker.labels["coder"]["queued"], "agent:code")
            self.assertTrue(config.pipeline.require_human_review)

    def test_rejects_automatic_merge(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "devloop.toml"
            path.write_text(BASE.replace("allow_merge = false", "allow_merge = true"), encoding="utf-8")
            with self.assertRaisesRegex(ConfigError, "forbids automatic merge"):
                load_config(path)

    def test_rejects_forwarding_the_tracker_credential(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "devloop.toml"
            path.write_text(
                BASE.replace(
                    'provider = "dry-run"',
                    'provider = "command"\ncommand = ["agent"]\npass_env = ["GITHUB_TOKEN"]',
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ConfigError, "cannot forward tracker credential"):
                load_config(path)


if __name__ == "__main__":
    unittest.main()
