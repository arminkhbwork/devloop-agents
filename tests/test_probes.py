import sys
import unittest

from devloop_agents.config import ProbeConfig
from devloop_agents.probes import execute_probe


class ProbeTest(unittest.TestCase):
    def test_command_probe_reports_health(self) -> None:
        result = execute_probe(
            ProbeConfig("python", "command", f"{sys.executable} -c 'raise SystemExit(0)'")
        )
        self.assertTrue(result.healthy)
        self.assertEqual(len(result.fingerprint), 16)

    def test_command_probe_reports_failure(self) -> None:
        result = execute_probe(
            ProbeConfig("python", "command", f"{sys.executable} -c 'raise SystemExit(3)'")
        )
        self.assertFalse(result.healthy)
        self.assertIn("exited 3", result.summary)


if __name__ == "__main__":
    unittest.main()

