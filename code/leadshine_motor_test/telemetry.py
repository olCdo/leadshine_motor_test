from __future__ import annotations

from dataclasses import dataclass

from .canopen import CanopenClient, SdoAbortError
from .drive import StatusWord
from .pdo import pulse_per_second_to_rpm


@dataclass(frozen=True)
class TelemetryValue:
    value: int | None
    error: str | None = None

    @property
    def available(self) -> bool:
        return self.value is not None


@dataclass(frozen=True)
class DriveStatusSnapshot:
    status_word: StatusWord
    actual_velocity_pulse_s: TelemetryValue
    actual_velocity_rpm: float | None
    bus_voltage_raw: TelemetryValue
    current_actual_value_raw: TelemetryValue
    torque_actual_value_raw: TelemetryValue
    temperature_raw: TelemetryValue


def read_drive_status(client: CanopenClient, pulses_per_rev: int) -> DriveStatusSnapshot:
    """Read status telemetry without writing control words."""

    status = StatusWord(client.sdo_read(0x6041, 0x00))
    actual_velocity = _read_optional(client, 0x606C, 0x00, signed=True)
    actual_velocity_rpm = (
        pulse_per_second_to_rpm(actual_velocity.value, pulses_per_rev)
        if actual_velocity.value is not None
        else None
    )

    return DriveStatusSnapshot(
        status_word=status,
        actual_velocity_pulse_s=actual_velocity,
        actual_velocity_rpm=actual_velocity_rpm,
        bus_voltage_raw=_read_optional(client, 0x6079, 0x00),
        current_actual_value_raw=_read_optional(client, 0x6078, 0x00, signed=True),
        torque_actual_value_raw=_read_optional(client, 0x6077, 0x00, signed=True),
        temperature_raw=_read_optional(client, 0x5502, 0x06, signed=True),
    )


def _read_optional(
    client: CanopenClient,
    index: int,
    subindex: int,
    signed: bool = False,
) -> TelemetryValue:
    try:
        return TelemetryValue(client.sdo_read(index, subindex, signed=signed))
    except SdoAbortError as exc:
        return TelemetryValue(None, str(exc))
