from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from .pdo import configure_velocity_pdos, encode_rpdo1_control_velocity, rpm_to_pulse_per_second
from .canopen import CanMessage, CanopenClient


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
    mode_display: int
    status_word: StatusWord
    acceleration_pulse_s2: int
    deceleration_pulse_s2: int


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

    mode_display = client.sdo_read(0x6061, 0x00, signed=True)
    status = StatusWord(client.sdo_read(0x6041, 0x00))
    return VelocityModePreparation(
        mode_display=mode_display,
        status_word=status,
        acceleration_pulse_s2=acceleration,
        deceleration_pulse_s2=deceleration,
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
