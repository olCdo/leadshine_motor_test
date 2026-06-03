from __future__ import annotations

import argparse

from . import __version__
from .config import AppConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="leadshine-motor-test",
        description=(
            "Leadshine LD2-CAN motor test CLI skeleton. "
            "CANopen PDO control is not implemented in this step."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--interface", default=AppConfig.interface, help="SocketCAN interface, default: can0")
    parser.add_argument("--bitrate", type=int, default=AppConfig.bitrate, help="CAN bitrate, default: 1000000")
    parser.add_argument("--node-id", type=int, default=AppConfig.node_id, help="CANopen node ID, default: 1")
    parser.add_argument("--max-rpm", type=int, default=AppConfig.max_rpm, help="Speed limit in rpm, default: 500")
    parser.add_argument(
        "--accel-rpm-s",
        type=int,
        default=AppConfig.accel_rpm_s,
        help="Acceleration limit in rpm/s, default: 500",
    )
    parser.add_argument(
        "--decel-rpm-s",
        type=int,
        default=AppConfig.decel_rpm_s,
        help="Deceleration limit in rpm/s, default: 500",
    )
    parser.add_argument(
        "--pulses-per-rev",
        type=int,
        default=AppConfig.pulses_per_rev,
        help="Pulse count per motor revolution, default: 10000",
    )
    parser.add_argument("--log-dir", default=AppConfig.log_dir, help="CSV log directory, default: logs")
    parser.add_argument(
        "--show-config",
        action="store_true",
        help="Print resolved configuration and exit.",
    )
    return parser


def config_from_args(args: argparse.Namespace) -> AppConfig:
    config = AppConfig(
        interface=args.interface,
        bitrate=args.bitrate,
        node_id=args.node_id,
        max_rpm=args.max_rpm,
        accel_rpm_s=args.accel_rpm_s,
        decel_rpm_s=args.decel_rpm_s,
        pulses_per_rev=args.pulses_per_rev,
        log_dir=args.log_dir,
    )
    config.validate()
    return config


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = config_from_args(args)

    if args.show_config:
        for field_name, value in config.__dict__.items():
            print(f"{field_name}={value}")
        return 0

    parser.print_help()
    return 0
