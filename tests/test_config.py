import unittest

from leadshine_motor_test.config import AppConfig


class AppConfigTest(unittest.TestCase):
    def test_default_config_is_valid(self) -> None:
        AppConfig().validate()

    def test_node_id_range_is_enforced(self) -> None:
        with self.assertRaises(ValueError):
            AppConfig(node_id=0).validate()

        with self.assertRaises(ValueError):
            AppConfig(node_id=128).validate()


if __name__ == "__main__":
    unittest.main()
