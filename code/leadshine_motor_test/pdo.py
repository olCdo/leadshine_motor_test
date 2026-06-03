from __future__ import annotations

from dataclasses import dataclass

from .canopen import CanMessage


@dataclass(frozen=True)
class PdoMappingEntry:
    index: int
    subindex: int
    bit_length: int

    def to_mapping_value(self) -> int:
        if not 0 <= self.index <= 0xFFFF:
            raise ValueError("index must be in range 0x0000..0xFFFF")
        if not 0 <= self.subindex <= 0xFF:
            raise ValueError("subindex must be in range 0x00..0xFF")
        if self.bit_length not in (8, 16, 32):
            raise ValueError("PDO mapping bit_length must be 8, 16, or 32")
        return (self.index << 16) | (self.subindex << 8) | self.bit_length


RPDO1_COB_BASE = 0x200
TPDO1_COB_BASE = 0x180

RPDO1_CONTROL_WORD_TARGET_VELOCITY = (
    PdoMappingEntry(0x6040, 0x00, 16),
    PdoMappingEntry(0x60FF, 0x00, 32),
)

TPDO1_STATUS_WORD_ACTUAL_VELOCITY = (
    PdoMappingEntry(0x6041, 0x00, 16),
    PdoMappingEntry(0x606C, 0x00, 32),
)


@dataclass(frozen=True)
class Tpdo1StatusVelocity:
    status_word: int
    actual_velocity_pulse_s: int


def rpm_to_pulse_per_second(rpm: float, pulses_per_rev: int) -> int:
    if pulses_per_rev <= 0:
        raise ValueError("pulses_per_rev must be positive")
    return round(rpm * pulses_per_rev / 60)


def pulse_per_second_to_rpm(pulse_per_second: int, pulses_per_rev: int) -> float:
    if pulses_per_rev <= 0:
        raise ValueError("pulses_per_rev must be positive")
    return pulse_per_second * 60 / pulses_per_rev


def encode_rpdo1_control_velocity(
    node_id: int,
    control_word: int,
    target_velocity_pulse_s: int,
) -> CanMessage:
    _validate_node_id(node_id)
    if not 0 <= control_word <= 0xFFFF:
        raise ValueError("control_word must be in range 0x0000..0xFFFF")
    data = control_word.to_bytes(2, byteorder="little", signed=False)
    data += int(target_velocity_pulse_s).to_bytes(4, byteorder="little", signed=True)
    return CanMessage(arbitration_id=RPDO1_COB_BASE + node_id, data=data)


def decode_tpdo1_status_velocity(message: CanMessage, node_id: int) -> Tpdo1StatusVelocity:
    _validate_node_id(node_id)
    expected_id = TPDO1_COB_BASE + node_id
    if message.arbitration_id != expected_id:
        raise ValueError("unexpected TPDO1 arbitration ID")
    if len(message.data) < 6:
        raise ValueError("TPDO1 status/velocity payload must contain at least 6 bytes")
    status_word = int.from_bytes(message.data[0:2], byteorder="little", signed=False)
    actual_velocity = int.from_bytes(message.data[2:6], byteorder="little", signed=True)
    return Tpdo1StatusVelocity(status_word=status_word, actual_velocity_pulse_s=actual_velocity)


def _validate_node_id(node_id: int) -> None:
    if not 1 <= node_id <= 127:
        raise ValueError("node_id must be in range 1..127")
