from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path
from time import sleep

from . import __version__
from .canopen import (
    CanMessage,
    CanopenClient,
    NmtCommand,
    SdoAbortError,
    SdoTimeoutError,
    decode_sdo_upload_response,
    encode_nmt,
    encode_sdo_download_request,
    encode_sdo_upload_request,
)
from .config import AppConfig
from .controller import MotorController
from .drive import (
    FIRST_MOTION_TEST_LIMIT_RPM,
    MAX_SPEED_TEST_DURATION_S,
    StatusWord,
    build_velocity_command,
    disable_control_sequence,
    enable_control_sequence,
    prepare_velocity_mode,
    run_limited_speed_test,
    run_zero_speed_enable_test,
)
from .monitor import TpdoStatusSample, read_tpdo1_status_sample
from .pdo import (
    RPDO1_CONTROL_WORD_TARGET_VELOCITY,
    TPDO1_STATUS_WORD_ACTUAL_VELOCITY,
    configure_velocity_pdos,
    decode_tpdo1_status_velocity,
    encode_rpdo1_control_velocity,
    pulse_per_second_to_rpm,
    rpm_to_pulse_per_second,
)
from .simulator import SimulatedCanBus
from .socketcan import SocketCanBus, SocketCanError
from .telemetry import DriveStatusSnapshot, TelemetryValue, read_drive_status


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="leadshine-motor-test",
        description=(
            "Leadshine LD2-CAN motor test CLI for CANopen communication, "
            "PDO setup, safe enable checks, and telemetry reads."
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
    parser.add_argument("--simulate", action="store_true", help="Use local simulated CANopen drive instead of SocketCAN.")
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
    parser.add_argument(
        "--configure-pdo-mapping",
        action="store_true",
        help="Temporarily configure RPDO1/TPDO1 mapping via SDO. Does not enable or move the motor.",
    )
    parser.add_argument(
        "--check-drive-codecs",
        action="store_true",
        help="Run offline drive status/control safety checks and exit.",
    )
    parser.add_argument(
        "--prepare-velocity-mode",
        action="store_true",
        help="Configure PDOs and Profile Velocity Mode via SDO. Does not enable or move the motor.",
    )
    parser.add_argument(
        "--zero-speed-enable-test",
        action="store_true",
        help="Enable with RPDO target velocity 0, then disable. Does not command motor motion.",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Read drive status and telemetry via SDO. Does not enable or move the motor.",
    )
    parser.add_argument(
        "--speed-test-rpm",
        type=float,
        help=f"Run one bounded speed test, limited to {FIRST_MOTION_TEST_LIMIT_RPM} rpm in this stage.",
    )
    parser.add_argument(
        "--speed-test-duration",
        type=float,
        default=2.0,
        help=f"Speed test duration in seconds, default: 2.0, max: {MAX_SPEED_TEST_DURATION_S:g}",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Start interactive motor control shell: enable, disable, speed <rpm>, stop, status, watch, quit.",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Periodically read status and telemetry. Does not enable or move the motor.",
    )
    parser.add_argument("--watch-period", type=float, default=1.0, help="Watch interval in seconds, default: 1.0")
    parser.add_argument("--watch-samples", type=int, default=0, help="Watch sample count, 0 means until Ctrl+C")
    parser.add_argument("--csv-log", action="store_true", help="Write watch samples to CSV under --log-dir")
    parser.add_argument(
        "--watch-pdo",
        action="store_true",
        help="Configure velocity PDOs, then watch TPDO1 status/actual velocity. Does not enable or move the motor.",
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
        return _run_canopen_comm_check(config, simulate=args.simulate)

    if args.check_pdo_codecs:
        _run_pdo_codec_check(config)
        return 0

    if args.configure_pdo_mapping:
        return _run_pdo_mapping_config(config, simulate=args.simulate)

    if args.check_drive_codecs:
        _run_drive_codec_check(config)
        return 0

    if args.prepare_velocity_mode:
        return _run_prepare_velocity_mode(config, simulate=args.simulate)

    if args.zero_speed_enable_test:
        return _run_zero_speed_enable_test(config, simulate=args.simulate)

    if args.status:
        return _run_status(config, simulate=args.simulate)

    if args.speed_test_rpm is not None:
        return _run_speed_test(
            config,
            target_rpm=args.speed_test_rpm,
            duration_s=args.speed_test_duration,
            simulate=args.simulate,
        )

    if args.interactive:
        return _run_interactive(config, simulate=args.simulate)

    if args.watch:
        return _run_watch(config, args.watch_period, args.watch_samples, args.csv_log, simulate=args.simulate)

    if args.watch_pdo:
        return _run_watch_pdo(config, args.watch_period, args.watch_samples, simulate=args.simulate)

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


def _run_canopen_comm_check(config: AppConfig, simulate: bool = False) -> int:
    _print_bus_opening(config, simulate)
    print("test_type=communication")
    print("motor_motion=no")
    print("action=read 6041 status word via SDO")
    try:
        with _open_bus(config, simulate) as bus:
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


def _run_pdo_mapping_config(config: AppConfig, simulate: bool = False) -> int:
    _print_bus_opening(config, simulate)
    print("test_type=communication")
    print("motor_motion=no")
    print("action=configure temporary RPDO1/TPDO1 mapping via SDO")
    print("writes_control_word=no")
    print("stores_parameters=no")
    try:
        with _open_bus(config, simulate) as bus:
            client = CanopenClient(bus, node_id=config.node_id, timeout=config.timeout)
            result = configure_velocity_pdos(client)
    except SdoTimeoutError as exc:
        print("result=timeout")
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
    print(f"rpdo1_cob_id=0x{result.rpdo1_cob_id:03X}")
    print(f"tpdo1_cob_id=0x{result.tpdo1_cob_id:03X}")
    print("rpdo1_mapping=" + ",".join(f"0x{value:08X}" for value in result.rpdo1_mapping))
    print("tpdo1_mapping=" + ",".join(f"0x{value:08X}" for value in result.tpdo1_mapping))
    return 0


def _run_drive_codec_check(config: AppConfig) -> None:
    status = StatusWord(0x0027)
    command = build_velocity_command(
        node_id=config.node_id,
        control_word=0x000F,
        target_rpm=120,
        max_rpm=config.max_rpm,
        pulses_per_rev=config.pulses_per_rev,
    )

    print("test_type=offline")
    print("motor_motion=no")
    print(f"status_word=0x{status.raw:04X}")
    print(f"state={status.state_label()}")
    print("enable_sequence=" + ",".join(f"0x{value:04X}" for value in enable_control_sequence()))
    print("disable_sequence=" + ",".join(f"0x{value:04X}" for value in disable_control_sequence()))
    print(f"target_rpm={command.target_rpm:g}")
    print(f"target_velocity_pulse_s={command.target_velocity_pulse_s}")
    print(f"rpdo1={command.frame.arbitration_id:03X}:{command.frame.data.hex()}")


def _run_prepare_velocity_mode(config: AppConfig, simulate: bool = False) -> int:
    _print_bus_opening(config, simulate)
    print("test_type=communication")
    print("motor_motion=no")
    print("action=prepare Profile Velocity Mode via SDO")
    print("writes_control_word=no")
    print("target_velocity=0")
    print("stores_parameters=no")
    try:
        with _open_bus(config, simulate) as bus:
            client = CanopenClient(bus, node_id=config.node_id, timeout=config.timeout)
            result = prepare_velocity_mode(
                client,
                accel_rpm_s=config.accel_rpm_s,
                decel_rpm_s=config.decel_rpm_s,
                pulses_per_rev=config.pulses_per_rev,
            )
    except SdoTimeoutError as exc:
        print("result=timeout")
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

    print("result=ok" if result.display_matches else "result=warning")
    print(f"mode_set={result.mode_set}")
    print(f"mode_display={result.mode_display}")
    print(f"status_word=0x{result.status_word.raw:04X}")
    print(f"state={result.status_word.state_label()}")
    print(f"acceleration_pulse_s2={result.acceleration_pulse_s2}")
    print(f"deceleration_pulse_s2={result.deceleration_pulse_s2}")
    return 0


def _run_zero_speed_enable_test(config: AppConfig, simulate: bool = False) -> int:
    _print_bus_opening(config, simulate)
    print("test_type=enable")
    print("motor_motion=not_commanded")
    print("action=enable briefly with RPDO target velocity 0, then disable")
    print("target_velocity=0")
    print("stores_parameters=no")
    try:
        with _open_bus(config, simulate) as bus:
            client = CanopenClient(bus, node_id=config.node_id, timeout=config.timeout)
            result = run_zero_speed_enable_test(
                client,
                accel_rpm_s=config.accel_rpm_s,
                decel_rpm_s=config.decel_rpm_s,
                pulses_per_rev=config.pulses_per_rev,
            )
    except SdoTimeoutError as exc:
        print("result=timeout")
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

    print("result=ok" if result.after_enable.operation_enabled else "result=warning")
    print(f"mode_display={result.prepared.mode_display}")
    print(f"after_shutdown=0x{result.after_shutdown.raw:04X}:{result.after_shutdown.state_label()}")
    print(f"after_switch_on=0x{result.after_switch_on.raw:04X}:{result.after_switch_on.state_label()}")
    print(f"after_enable=0x{result.after_enable.raw:04X}:{result.after_enable.state_label()}")
    print(f"after_disable=0x{result.after_disable.raw:04X}:{result.after_disable.state_label()}")
    print(f"after_final_shutdown=0x{result.after_final_shutdown.raw:04X}:{result.after_final_shutdown.state_label()}")
    return 0


def _run_speed_test(
    config: AppConfig,
    target_rpm: float,
    duration_s: float,
    simulate: bool = False,
) -> int:
    _print_bus_opening(config, simulate)
    print("test_type=motion")
    print("motor_motion=yes")
    print("action=run one bounded Profile Velocity Mode speed test, then stop and disable")
    print(f"target_rpm={target_rpm:g}")
    print(f"duration_s={duration_s:g}")
    print(f"safety_limit_rpm={min(config.max_rpm, FIRST_MOTION_TEST_LIMIT_RPM)}")
    print("stores_parameters=no")
    try:
        with _open_bus(config, simulate) as bus:
            client = CanopenClient(bus, node_id=config.node_id, timeout=config.timeout)
            result = run_limited_speed_test(
                client,
                target_rpm=target_rpm,
                duration_s=duration_s,
                max_rpm=config.max_rpm,
                accel_rpm_s=config.accel_rpm_s,
                decel_rpm_s=config.decel_rpm_s,
                pulses_per_rev=config.pulses_per_rev,
            )
    except (SdoTimeoutError, SdoAbortError) as exc:
        print("result=canopen_error")
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
    print(f"mode_display={result.prepared.mode_display}")
    print(f"target_velocity_pulse_s={result.target_velocity_pulse_s}")
    print(f"after_enable=0x{result.after_enable.raw:04X}:{result.after_enable.state_label()}")
    print(f"during_run=0x{result.during_run.raw:04X}:{result.during_run.state_label()}")
    print(f"actual_velocity_pulse_s={result.actual_velocity_pulse_s}")
    print(f"actual_velocity_rpm={result.actual_velocity_rpm:.3f}")
    print(f"after_zero_speed=0x{result.after_zero_speed.raw:04X}:{result.after_zero_speed.state_label()}")
    print(f"after_disable=0x{result.after_disable.raw:04X}:{result.after_disable.state_label()}")
    print(f"after_final_shutdown=0x{result.after_final_shutdown.raw:04X}:{result.after_final_shutdown.state_label()}")
    return 0


def _run_status(config: AppConfig, simulate: bool = False) -> int:
    _print_bus_opening(config, simulate)
    print("test_type=communication")
    print("motor_motion=no")
    print("action=read drive status and telemetry via SDO")
    print("writes_control_word=no")
    try:
        with _open_bus(config, simulate) as bus:
            client = CanopenClient(bus, node_id=config.node_id, timeout=config.timeout)
            snapshot = read_drive_status(client, pulses_per_rev=config.pulses_per_rev)
    except SdoTimeoutError as exc:
        print("result=timeout")
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
    _print_snapshot(snapshot)
    return 0


def _run_interactive(config: AppConfig, simulate: bool = False) -> int:
    _print_bus_opening(config, simulate)
    print("test_type=interactive_motion_control")
    print("motor_motion=commanded_by_speed")
    print(f"max_rpm={config.max_rpm}")
    print("exit_action=stop_then_disable")
    print("commands=enable,disable,speed <rpm>,stop,status,watch [samples] [period],help,quit")
    controller: MotorController | None = None
    try:
        with _open_bus(config, simulate) as bus:
            client = CanopenClient(bus, node_id=config.node_id, timeout=config.timeout)
            controller = MotorController(
                client,
                max_rpm=config.max_rpm,
                accel_rpm_s=config.accel_rpm_s,
                decel_rpm_s=config.decel_rpm_s,
                pulses_per_rev=config.pulses_per_rev,
            )
            prepared = controller.prepare()
            print("result=ready")
            print(f"mode_display={prepared.mode_display}")
            while True:
                try:
                    line = input("leadshine> ").strip()
                except EOFError:
                    break
                if not line:
                    continue
                if _handle_interactive_command(controller, line):
                    break
    except KeyboardInterrupt:
        print()
        print("result=interrupted")
    except (SdoTimeoutError, SdoAbortError) as exc:
        print("result=canopen_error")
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
    finally:
        if controller is not None:
            controller.safe_shutdown()
            print("safe_shutdown=done")
    return 0


def _run_watch(
    config: AppConfig,
    period_s: float,
    samples: int,
    csv_log: bool,
    simulate: bool = False,
) -> int:
    if period_s <= 0:
        print("result=error")
        print("error=watch_period must be positive")
        return 2
    if samples < 0:
        print("result=error")
        print("error=watch_samples must be >= 0")
        return 2

    csv_file = None
    writer = None
    csv_path = None
    try:
        if csv_log:
            csv_path = _new_csv_path(config.log_dir)
            csv_file = csv_path.open("w", newline="", encoding="utf-8")
            writer = csv.DictWriter(csv_file, fieldnames=_csv_fieldnames())
            writer.writeheader()

        _print_bus_opening(config, simulate)
        print("test_type=watch")
        print("motor_motion=no")
        print("writes_control_word=no")
        print(f"watch_period_s={period_s:g}")
        print(f"watch_samples={samples}")
        if csv_path is not None:
            print(f"csv_path={csv_path}")
        with _open_bus(config, simulate) as bus:
            client = CanopenClient(bus, node_id=config.node_id, timeout=config.timeout)
            count = 0
            while samples == 0 or count < samples:
                snapshot = read_drive_status(client, pulses_per_rev=config.pulses_per_rev)
                count += 1
                print(_snapshot_summary(count, snapshot))
                if writer is not None:
                    writer.writerow(_snapshot_row(snapshot))
                    csv_file.flush()
                if samples == 0 or count < samples:
                    sleep(period_s)
    except KeyboardInterrupt:
        print()
        print("result=interrupted")
        return 0
    except (SdoTimeoutError, SdoAbortError) as exc:
        print("result=canopen_error")
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
    finally:
        if csv_file is not None:
            csv_file.close()

    print("result=ok")
    return 0


def _run_watch_pdo(
    config: AppConfig,
    period_s: float,
    samples: int,
    simulate: bool = False,
) -> int:
    if period_s < 0:
        print("result=error")
        print("error=watch_period must be >= 0")
        return 2
    if samples < 0:
        print("result=error")
        print("error=watch_samples must be >= 0")
        return 2

    _print_bus_opening(config, simulate)
    print("test_type=tpdo_watch")
    print("motor_motion=no")
    print("writes_control_word=no")
    print("action=configure velocity PDOs and read TPDO1 status/actual velocity")
    print(f"watch_samples={samples}")
    try:
        with _open_bus(config, simulate) as bus:
            client = CanopenClient(bus, node_id=config.node_id, timeout=config.timeout)
            prepared = prepare_velocity_mode(
                client,
                accel_rpm_s=config.accel_rpm_s,
                decel_rpm_s=config.decel_rpm_s,
                pulses_per_rev=config.pulses_per_rev,
            )
            print("result=ready" if prepared.display_matches else "result=warning")
            print(f"mode_display={prepared.mode_display}")
            if not prepared.display_matches:
                return 2
            count = 0
            while samples == 0 or count < samples:
                sample = read_tpdo1_status_sample(
                    bus,
                    node_id=config.node_id,
                    pulses_per_rev=config.pulses_per_rev,
                    timeout=config.timeout,
                )
                count += 1
                print(_tpdo_summary(count, sample))
                if samples == 0 or count < samples:
                    sleep(period_s)
    except KeyboardInterrupt:
        print()
        print("result=interrupted")
        return 0
    except (TimeoutError, SdoTimeoutError, SdoAbortError) as exc:
        print("result=canopen_error")
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
    return 0


def _handle_interactive_command(controller: MotorController, line: str) -> bool:
    parts = line.split()
    command = parts[0].lower()
    if command in ("quit", "exit"):
        return True
    if command == "help":
        print("commands=enable,disable,speed <rpm>,stop,status,watch [samples] [period],help,quit")
        return False
    if command == "enable":
        status = controller.enable()
        print(f"enabled=0x{status.raw:04X}:{status.state_label()}")
        return False
    if command == "disable":
        status = controller.disable()
        print(f"disabled=0x{status.raw:04X}:{status.state_label()}")
        return False
    if command == "stop":
        status = controller.stop()
        print(f"stopped=0x{status.raw:04X}:{status.state_label()}")
        return False
    if command == "speed":
        if len(parts) != 2:
            print("error=usage: speed <rpm>")
            return False
        try:
            rpm = float(parts[1])
            velocity = controller.set_speed(rpm)
        except ValueError as exc:
            print(f"error={exc}")
            return False
        print(f"target_rpm={velocity.target_rpm:g}")
        print(f"target_velocity_pulse_s={velocity.target_velocity_pulse_s}")
        return False
    if command == "status":
        _print_snapshot(controller.status())
        return False
    if command == "watch":
        try:
            samples = int(parts[1]) if len(parts) >= 2 else 5
            period = float(parts[2]) if len(parts) >= 3 else 1.0
        except ValueError as exc:
            print(f"error={exc}")
            return False
        if samples <= 0:
            print("error=watch samples must be positive")
            return False
        if period <= 0:
            print("error=watch period must be positive")
            return False
        for index in range(1, samples + 1):
            print(_snapshot_summary(index, controller.status()))
            if index < samples:
                sleep(period)
        return False
    print("error=unknown command; type help")
    return False


def _print_value(name: str, telemetry: TelemetryValue) -> None:
    if telemetry.value is None:
        print(f"{name}=unavailable")
        if telemetry.error:
            print(f"{name}_error={telemetry.error}")
        return
    print(f"{name}={telemetry.value}")


def _bool_text(value: bool) -> str:
    return "yes" if value else "no"


def _print_snapshot(snapshot: DriveStatusSnapshot) -> None:
    print(f"status_word=0x{snapshot.status_word.raw:04X}")
    print(f"state={snapshot.status_word.state_label()}")
    print(f"operation_enabled={_bool_text(snapshot.status_word.operation_enabled)}")
    print(f"fault={_bool_text(snapshot.status_word.fault)}")
    print(f"warning={_bool_text(snapshot.status_word.warning)}")
    _print_value("actual_velocity_pulse_s", snapshot.actual_velocity_pulse_s)
    if snapshot.actual_velocity_rpm is None:
        print("actual_velocity_rpm=unavailable")
    else:
        print(f"actual_velocity_rpm={snapshot.actual_velocity_rpm:.3f}")
    _print_value("bus_voltage_raw", snapshot.bus_voltage_raw)
    _print_value("current_actual_value_raw", snapshot.current_actual_value_raw)
    _print_value("torque_actual_value_raw", snapshot.torque_actual_value_raw)
    _print_value("temperature_raw", snapshot.temperature_raw)


def _snapshot_summary(index: int, snapshot: DriveStatusSnapshot) -> str:
    rpm = "unavailable" if snapshot.actual_velocity_rpm is None else f"{snapshot.actual_velocity_rpm:.3f}"
    voltage = _summary_value(snapshot.bus_voltage_raw)
    current = _summary_value(snapshot.current_actual_value_raw)
    torque = _summary_value(snapshot.torque_actual_value_raw)
    temp = _summary_value(snapshot.temperature_raw)
    return (
        f"sample={index} status_word=0x{snapshot.status_word.raw:04X} "
        f"state={snapshot.status_word.state_label()} enabled={_bool_text(snapshot.status_word.operation_enabled)} "
        f"rpm={rpm} bus_voltage_raw={voltage} current_raw={current} torque_raw={torque} temperature_raw={temp}"
    )


def _tpdo_summary(index: int, sample: TpdoStatusSample) -> str:
    return (
        f"sample={index} status_word=0x{sample.status_word.raw:04X} "
        f"state={sample.status_word.state_label()} enabled={_bool_text(sample.status_word.operation_enabled)} "
        f"actual_velocity_pulse_s={sample.actual_velocity_pulse_s} "
        f"actual_velocity_rpm={sample.actual_velocity_rpm:.3f}"
    )


def _summary_value(telemetry: TelemetryValue) -> str:
    return "unavailable" if telemetry.value is None else str(telemetry.value)


def _new_csv_path(log_dir: str) -> Path:
    directory = Path(log_dir)
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return directory / f"motor_watch_{timestamp}.csv"


def _csv_fieldnames() -> list[str]:
    return [
        "timestamp",
        "status_word",
        "state",
        "operation_enabled",
        "fault",
        "warning",
        "actual_velocity_pulse_s",
        "actual_velocity_rpm",
        "bus_voltage_raw",
        "current_actual_value_raw",
        "torque_actual_value_raw",
        "temperature_raw",
    ]


def _snapshot_row(snapshot: DriveStatusSnapshot) -> dict[str, object]:
    return {
        "timestamp": datetime.now().isoformat(timespec="milliseconds"),
        "status_word": f"0x{snapshot.status_word.raw:04X}",
        "state": snapshot.status_word.state_label(),
        "operation_enabled": _bool_text(snapshot.status_word.operation_enabled),
        "fault": _bool_text(snapshot.status_word.fault),
        "warning": _bool_text(snapshot.status_word.warning),
        "actual_velocity_pulse_s": _csv_value(snapshot.actual_velocity_pulse_s),
        "actual_velocity_rpm": "" if snapshot.actual_velocity_rpm is None else f"{snapshot.actual_velocity_rpm:.3f}",
        "bus_voltage_raw": _csv_value(snapshot.bus_voltage_raw),
        "current_actual_value_raw": _csv_value(snapshot.current_actual_value_raw),
        "torque_actual_value_raw": _csv_value(snapshot.torque_actual_value_raw),
        "temperature_raw": _csv_value(snapshot.temperature_raw),
    }


def _csv_value(telemetry: TelemetryValue) -> str | int:
    return "" if telemetry.value is None else telemetry.value


def _open_bus(config: AppConfig, simulate: bool):
    if simulate:
        return SimulatedCanBus(node_id=config.node_id, pulses_per_rev=config.pulses_per_rev)
    return SocketCanBus(config.interface)


def _print_bus_opening(config: AppConfig, simulate: bool) -> None:
    if simulate:
        print("opening_simulated_canopen=yes")
        print(f"simulated_node_id={config.node_id}")
        return
    print(f"opening_socketcan={config.interface}")
