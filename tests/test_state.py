import tempfile
import unittest
from pathlib import Path

from devloop_agents.state import LeaseBusy, StateStore


class StateStoreTest(unittest.TestCase):
    def test_prevents_duplicate_concurrent_lease(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = StateStore(Path(directory) / "state.db")
            with store.lease("coder:1", "run-a"):
                with self.assertRaises(LeaseBusy):
                    with store.lease("coder:1", "run-b"):
                        pass
            with store.lease("coder:1", "run-c"):
                pass


if __name__ == "__main__":
    unittest.main()

