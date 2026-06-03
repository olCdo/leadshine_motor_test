import unittest

from leadshine_motor_test.cli import build_parser, config_from_args


class CliTest(unittest.TestCase):
    def test_cli_args_build_config(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "--interface",
                "can1",
                "--bitrate",
                "500000",
                "--node-id",
                "2",
                "--max-rpm",
                "300",
                "--pulses-per-rev",
                "20000",
            ]
        )

        config = config_from_args(args)

        self.assertEqual(config.interface, "can1")
        self.assertEqual(config.bitrate, 500_000)
        self.assertEqual(config.node_id, 2)
        self.assertEqual(config.max_rpm, 300)
        self.assertEqual(config.pulses_per_rev, 20_000)


if __name__ == "__main__":
    unittest.main()
