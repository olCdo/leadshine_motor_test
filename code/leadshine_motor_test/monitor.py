from __future__ import annotations

from dataclasses import dataclass
from time import monotonic

from .canopen import CanBus
from .drive import StatusWord
from .pdo import decode_tpdo1_status_velocity, pulse_per_second_to_rpm


@dataclass(frozen=True)
class TpdoStatusSample:
    status_word: StatusWord
    actual_velocity_pulse_s: int
    actual_velocity_rpm: float


def read_tpdo1_status_sample(
    bus: CanBus,
    node_id: int,
    pulses_per_rev: int,
    timeout: float,
) -> TpdoStatusSample:
    expected_id = 0x180 + node_id
    deadline = monotonic() + timeout
    while monotonic() < deadline:
        remaining = max(0.0, deadline - monotonic())
        message = bus.recv(remaining)
        if message is None:
            break
        if message.arbitration_id != expected_id:
            continue
        decoded = decode_tpdo1_status_velocity(message, node_id=node_id)
        return TpdoStatusSample(
            status_word=StatusWord(decoded.status_word),
            actual_velocity_pulse_s=decoded.actual_velocity_pulse_s,
            actual_velocity_rpm=pulse_per_second_to_rpm(decoded.actual_velocity_pulse_s, pulses_per_rev),
        )
    raise TimeoutError(f"timeout waiting for TPDO1 0x{expected_id:03X}")
