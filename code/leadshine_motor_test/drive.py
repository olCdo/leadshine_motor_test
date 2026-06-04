from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from time import sleep

from .pdo import configure_velocity_pdos, encode_rpdo1_control_velocity, rpm_to_pulse_per_second
from .canopen import CanMessage, CanopenClient, NmtCommand


FIRST_MOTION_TEST_LIMIT_RPM = 50
MAX_SPEED_TEST_DURATION_S = 10.0


class ControlWord(IntEnum):
    SHUTDOWN = 0x0006
    SWITCH_ON = 0x0007
    ENABLE_OPERATION = 0x000F
    DISABLE_OPERATION = 0x0007
    FAULT_RESET = 0x0080


@dataclass(frozen=True)
class StatusWord:
    raw: int

    @property
    def ready_to_switch_on(self) -> bool:
        return bool(self.raw & (1 << 0))

    @property
    def switched_on(self) -> bool:
        return bool(self.raw & (1 << 1))

    @property
    def operation_enabled(self) -> bool:
        return bool(self.raw & (1 << 2))

    @property
    def fault(self) -> bool:
        return bool(self.raw & (1 << 3))

    @property
    def voltage_enabled(self) -> bool:
        return bool(self.raw & (1 << 4))

    @property
    def quick_stop(self) -> bool:
        return bool(self.raw & (1 << 5))

    @property
    def switch_on_disabled(self) -> bool:
        return bool(self.raw & (1 << 6))

    @property
    def warning(self) -> bool:
        return bool(self.raw & (1 << 7))

    @property
    def remote(self) -> bool:
        return bool(self.raw & (1 << 9))

    @property
    def target_reached(self) -> bool:
        return bool(self.raw & (1 << 10))

    @property
    def limit_active(self) -> bool:
        return bool(self.raw & (1 << 11))

    def state_label(self) -> str:
        masked = self.raw & 0x006F
        if masked == 0x0040:
            return "switch_on_disabled"
        if masked == 0x0021:
            return "ready_to_switch_on"
        if masked == 0x0023:
            return "switched_on"
        if masked == 0x0027:
            return "operation_enabled"
        if self.fault:
            return "fault"
        return "unknown"


@dataclass(frozen=True)
class VelocityCommand:
    control_word: int
    target_rpm: float
    target_velocity_pulse_s: int
    frame: CanMessage


@dataclass(frozen=True)
class VelocityModePreparation:
    mode_set: int
    mode_display: int
    status_word: StatusWord
    acceleration_pulse_s2: int
    deceleration_pulse_s2: int
    display_matches: bool


@dataclass(frozen=True)
class ZeroSpeedEnableResult:
    prepared: VelocityModePreparation
    after_shutdown: StatusWord
    after_switch_on: StatusWord
    after_enable: StatusWord
    after_disable: StatusWord
    after_final_shutdown: StatusWord


@dataclass(frozen=True)
class SpeedTestResult:
    prepared: VelocityModePreparation
    target_rpm: float
    target_velocity_pulse_s: int
    duration_s: float
    safety_limit_rpm: int
    after_enable: StatusWord
    during_run: StatusWord
    actual_velocity_pulse_s: int
    actual_velocity_rpm: float
    after_zero_speed: StatusWord
    after_disable: StatusWord
    after_final_shutdown: StatusWord


def rpm_per_second_to_pulse_per_second2(rpm_per_second: float, pulses_per_rev: int) -> int:
    if pulses_per_rev <= 0:
        raise ValueError("pulses_per_rev must be positive")
    return max(1, round(rpm_per_second * pulses_per_rev / 60))


def prepare_velocity_mode(
    client: CanopenClient,
    accel_rpm_s: int,
    decel_rpm_s: int,
    pulses_per_rev: int,
) -> VelocityModePreparation:
    """Prepare Profile Velocity Mode without enabling or moving the motor."""

    acceleration = rpm_per_second_to_pulse_per_second2(accel_rpm_s, pulses_per_rev)
    deceleration = rpm_per_second_to_pulse_per_second2(decel_rpm_s, pulses_per_rev)

    configure_velocity_pdos(client)
    client.sdo_write(0x6060, 0x00, 3, size=1, signed=True)
    client.sdo_write(0x6083, 0x00, acceleration, size=4)
    client.sdo_write(0x6084, 0x00, deceleration, size=4)
    client.sdo_write(0x60FF, 0x00, 0, size=4, signed=True)

    # NMT Operational is required by some drives before 6061 reflects 6060.
    client.send_nmt(NmtCommand.START_REMOTE_NODE)
    sleep(0.05)

    mode_set = client.sdo_read(0x6060, 0x00, signed=True)
    mode_display = client.sdo_read(0x6061, 0x00, signed=True)
    status = StatusWord(client.sdo_read(0x6041, 0x00))
    return VelocityModePreparation(
        mode_set=mode_set,
        mode_display=mode_display,
        status_word=status,
        acceleration_pulse_s2=acceleration,
        deceleration_pulse_s2=deceleration,
        display_matches=mode_display == 3,
    )


def build_velocity_command(
    node_id: int,
    control_word: int,
    target_rpm: float,
    max_rpm: int,
    pulses_per_rev: int,
) -> VelocityCommand:
    if max_rpm <= 0:
        raise ValueError("max_rpm must be positive")
    if abs(target_rpm) > max_rpm:
        raise ValueError(f"target rpm {target_rpm:g} exceeds max_rpm {max_rpm}")
    target_velocity = rpm_to_pulse_per_second(target_rpm, pulses_per_rev)
    frame = encode_rpdo1_control_velocity(node_id, control_word, target_velocity)
    return VelocityCommand(
        control_word=control_word,
        target_rpm=target_rpm,
        target_velocity_pulse_s=target_velocity,
        frame=frame,
    )


def run_zero_speed_enable_test(
    client: CanopenClient,
    accel_rpm_s: int,
    decel_rpm_s: int,
    pulses_per_rev: int,
) -> ZeroSpeedEnableResult:
    """Enable briefly with target velocity 0, then disable.

    Control is sent through RPDO1. Status checks use SDO reads. This command does
    not request motor motion because target velocity is always 0.
    """

    prepared = prepare_velocity_mode(client, accel_rpm_s, decel_rpm_s, pulses_per_rev)
    if not prepared.display_matches:
        raise ValueError("operation mode display is not Profile Velocity Mode")

    try:
        client.send_message(_zero_speed_frame(client.node_id, int(ControlWord.SHUTDOWN)))
        sleep(0.1)
        after_shutdown = StatusWord(client.sdo_read(0x6041, 0x00))

        client.send_message(_zero_speed_frame(client.node_id, int(ControlWord.SWITCH_ON)))
        sleep(0.1)
        after_switch_on = StatusWord(client.sdo_read(0x6041, 0x00))

        client.send_message(_zero_speed_frame(client.node_id, int(ControlWord.ENABLE_OPERATION)))
        sleep(0.2)
        after_enable = StatusWord(client.sdo_read(0x6041, 0x00))
    finally:
        client.send_message(_zero_speed_frame(client.node_id, int(ControlWord.DISABLE_OPERATION)))
        sleep(0.1)

    after_disable = StatusWord(client.sdo_read(0x6041, 0x00))
    client.send_message(_zero_speed_frame(client.node_id, int(ControlWord.SHUTDOWN)))
    sleep(0.1)
    after_final_shutdown = StatusWord(client.sdo_read(0x6041, 0x00))

    return ZeroSpeedEnableResult(
        prepared=prepared,
        after_shutdown=after_shutdown,
        after_switch_on=after_switch_on,
        after_enable=after_enable,
        after_disable=after_disable,
        after_final_shutdown=after_final_shutdown,
    )


def run_limited_speed_test(
    client: CanopenClient,
    target_rpm: float,
    duration_s: float,
    max_rpm: int,
    accel_rpm_s: int,
    decel_rpm_s: int,
    pulses_per_rev: int,
) -> SpeedTestResult:
    """Run one bounded low-speed movement, then command zero speed and disable."""

    safety_limit = min(max_rpm, FIRST_MOTION_TEST_LIMIT_RPM)
    if target_rpm == 0:
        raise ValueError("target_rpm must be non-zero for speed test")
    if abs(target_rpm) > safety_limit:
        raise ValueError(f"target_rpm {target_rpm:g} exceeds safety limit {safety_limit} rpm")
    if duration_s <= 0 or duration_s > MAX_SPEED_TEST_DURATION_S:
        raise ValueError(f"duration_s must be > 0 and <= {MAX_SPEED_TEST_DURATION_S:g}")

    prepared = prepare_velocity_mode(client, accel_rpm_s, decel_rpm_s, pulses_per_rev)
    if not prepared.display_matches:
        raise ValueError("operation mode display is not Profile Velocity Mode")

    target_command = build_velocity_command(
        node_id=client.node_id,
        control_word=int(ControlWord.ENABLE_OPERATION),
        target_rpm=target_rpm,
        max_rpm=safety_limit,
        pulses_per_rev=pulses_per_rev,
    )

    enable_command_sent = False
    after_zero_speed = StatusWord(0)
    after_disable = StatusWord(0)
    after_final_shutdown = StatusWord(0)
    try:
        client.send_message(_zero_speed_frame(client.node_id, int(ControlWord.SHUTDOWN)))
        sleep(0.1)

        client.send_message(_zero_speed_frame(client.node_id, int(ControlWord.SWITCH_ON)))
        sleep(0.1)

        client.send_message(_zero_speed_frame(client.node_id, int(ControlWord.ENABLE_OPERATION)))
        enable_command_sent = True
        sleep(0.2)
        after_enable = StatusWord(client.sdo_read(0x6041, 0x00))
        if not after_enable.operation_enabled:
            raise ValueError("drive did not reach operation_enabled before speed command")

        client.send_message(target_command.frame)
        sleep(duration_s)
        during_run = StatusWord(client.sdo_read(0x6041, 0x00))
        actual_velocity = client.sdo_read(0x606C, 0x00, signed=True)
    finally:
        if enable_command_sent:
            client.send_message(_zero_speed_frame(client.node_id, int(ControlWord.ENABLE_OPERATION)))
            sleep(_stop_wait_seconds(abs(target_rpm), decel_rpm_s))
            after_zero_speed = _read_status_or_unknown(client)
            client.send_message(_zero_speed_frame(client.node_id, int(ControlWord.DISABLE_OPERATION)))
            sleep(0.1)
            after_disable = _read_status_or_unknown(client)
            client.send_message(_zero_speed_frame(client.node_id, int(ControlWord.SHUTDOWN)))
            sleep(0.1)
            after_final_shutdown = _read_status_or_unknown(client)

    return SpeedTestResult(
        prepared=prepared,
        target_rpm=target_rpm,
        target_velocity_pulse_s=target_command.target_velocity_pulse_s,
        duration_s=duration_s,
        safety_limit_rpm=safety_limit,
        after_enable=after_enable,
        during_run=during_run,
        actual_velocity_pulse_s=actual_velocity,
        actual_velocity_rpm=actual_velocity * 60 / pulses_per_rev,
        after_zero_speed=after_zero_speed,
        after_disable=after_disable,
        after_final_shutdown=after_final_shutdown,
    )


def enable_control_sequence() -> tuple[int, int, int]:
    return (
        int(ControlWord.SHUTDOWN),
        int(ControlWord.SWITCH_ON),
        int(ControlWord.ENABLE_OPERATION),
    )


def disable_control_sequence() -> tuple[int, int]:
    return (
        int(ControlWord.DISABLE_OPERATION),
        int(ControlWord.SHUTDOWN),
    )


def _zero_speed_frame(node_id: int, control_word: int) -> CanMessage:
    return encode_rpdo1_control_velocity(node_id, control_word, 0)


def _stop_wait_seconds(target_rpm: float, decel_rpm_s: int) -> float:
    if decel_rpm_s <= 0:
        return 0.5
    return min(2.0, max(0.2, target_rpm / decel_rpm_s + 0.2))


def _read_status_or_unknown(client: CanopenClient) -> StatusWord:
    try:
        return StatusWord(client.sdo_read(0x6041, 0x00))
    except Exception:
        return StatusWord(0)
