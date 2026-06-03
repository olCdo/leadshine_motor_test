from __future__ import annotations

import argparse

from . import __version__
from .canopen import (
    CanMessage,
    CanopenClient,
    NmtCommand,
    SdoTimeoutError,
    decode_sdo_upload_response,
    encode_nmt,
    encode_sdo_download_request,
    encode_sdo_upload_request,
)
from .config import AppConfig
from .pdo import (
    RPDO1_CONTROL_WORD_TARGET_VELOCITY,
    TPDO1_STATUS_WORD_ACTUAL_VELOCITY,
    decode_tpdo1_status_velocity,
    encode_rpdo1_control_velocity,
    pulse_per_second_to_rpm,
    rpm_to_pulse_per_second,
)
from .socketcan import SocketCanBus, SocketCanError


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
    parser.add_argument("--timeout", type=float, default=AppConfig.timeout, help="SDO timeout in seconds, default: 1.0")
    parser.add_argument(
        "--show-config",
        action="store_true",
        help="Print resolved configuration and exit.",
    )
    parser.add_argument(
        "--check-canopen-codecs",
        action="store_true",
        help="Run offline CANopen NMT/SDO codec checks and exit.",
    )
    parser.add_argument(
        "--check-canopen-comm",
        action="store_true",
        help="Open SocketCAN and read 6041 status word via SDO. Does not enable or move the motor.",
    )
    parser.add_argument(
        "--check-pdo-codecs",
        action="store_true",
        help="Run offline PDO mapping and payload codec checks and exit.",
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
        timeout=args.timeout,
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

    if args.check_canopen_codecs:
        _run_canopen_codec_check(config)
        return 0

    if args.check_canopen_comm:
        return _run_canopen_comm_check(config)

    if args.check_pdo_codecs:
        _run_pdo_codec_check(config)
        return 0

    parser.print_help()
    return 0


def _run_canopen_codec_check(config: AppConfig) -> None:
    nmt = encode_nmt(NmtCommand.START_REMOTE_NODE, config.node_id)
    upload = encode_sdo_upload_request(config.node_id, 0x6041, 0)
    download = encode_sdo_download_request(config.node_id, 0x6060, 0, 3, size=1, signed=True)
    response = CanMessage(
        arbitration_id=0x580 + config.node_id,
        data=bytes([0x4B, 0x41, 0x60, 0x00, 0x37, 0x12, 0x00, 0x00]),
    )
    decoded = decode_sdo_upload_response(response, config.node_id, 0x6041, 0)

    print(f"nmt={nmt.arbitration_id:03X}:{nmt.data.hex()}")
    print(f"sdo_upload={upload.arbitration_id:03X}:{upload.data.hex()}")
    print(f"sdo_download={download.arbitration_id:03X}:{download.data.hex()}")
    print(f"decoded_status_word=0x{decoded:04X}")


def _run_canopen_comm_check(config: AppConfig) -> int:
    print(f"opening_socketcan={config.interface}")
    print("test_type=communication")
    print("motor_motion=no")
    print("action=read 6041 status word via SDO")
    try:
        with SocketCanBus(config.interface) as bus:
            client = CanopenClient(bus, node_id=config.node_id, timeout=config.timeout)
            status_word = client.sdo_read(0x6041, 0)
    except SdoTimeoutError as exc:
        print(f"result=timeout")
        print(f"error={exc}")
        return 2
    except SocketCanError as exc:
        print("result=socketcan_error")
        print(f"error={exc}")
        return 2
    except Exception as exc:
        print("result=error")
        print(f"error={exc}")
        return 2

    print("result=ok")
    print(f"status_word=0x{status_word:04X}")
    return 0


def _run_pdo_codec_check(config: AppConfig) -> None:
    target_velocity = rpm_to_pulse_per_second(120, config.pulses_per_rev)
    rpdo = encode_rpdo1_control_velocity(
        node_id=config.node_id,
        control_word=0x000F,
        target_velocity_pulse_s=target_velocity,
    )
    decoded = decode_tpdo1_status_velocity(
        CanMessage(
            arbitration_id=0x180 + config.node_id,
            data=bytes.fromhex("3701204e0000"),
        ),
        node_id=config.node_id,
    )
    actual_rpm = pulse_per_second_to_rpm(decoded.actual_velocity_pulse_s, config.pulses_per_rev)

    print("test_type=offline")
    print("motor_motion=no")
    print("rpdo1_mapping=" + ",".join(f"0x{entry.to_mapping_value():08X}" for entry in RPDO1_CONTROL_WORD_TARGET_VELOCITY))
    print("tpdo1_mapping=" + ",".join(f"0x{entry.to_mapping_value():08X}" for entry in TPDO1_STATUS_WORD_ACTUAL_VELOCITY))
    print(f"rpdo1={rpdo.arbitration_id:03X}:{rpdo.data.hex()}")
    print(f"decoded_status_word=0x{decoded.status_word:04X}")
    print(f"decoded_actual_velocity_pulse_s={decoded.actual_velocity_pulse_s}")
    print(f"decoded_actual_velocity_rpm={actual_rpm:.3f}")
