import unittest

from app import greet


class GreetingTest(unittest.TestCase):
    def test_named_greeting(self) -> None:
        self.assertEqual(greet("Ada"), "Hello, Ada!")

    def test_empty_name_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            greet("  ")


if __name__ == "__main__":
    unittest.main()

