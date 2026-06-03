from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from time import monotonic
from typing import Protocol


class CanBus(Protocol):
    """Minimal CAN bus protocol used by the CANopen layer."""

    def send(self, arbitration_id: int, data: bytes) -> None:
        """Send one standard CAN frame."""

    def recv(self, timeout: float | None = None) -> CanMessage | None:
        """Receive one CAN frame, or return None on timeout."""


@dataclass(frozen=True)
class CanMessage:
    arbitration_id: int
    data: bytes


class NmtCommand(IntEnum):
    START_REMOTE_NODE = 0x01
    STOP_REMOTE_NODE = 0x02
    ENTER_PRE_OPERATIONAL = 0x80
    RESET_NODE = 0x81
    RESET_COMMUNICATION = 0x82


class SdoAbortError(RuntimeError):
    def __init__(self, index: int, subindex: int, abort_code: int) -> None:
        super().__init__(
            f"SDO abort for 0x{index:04X}:{subindex:02X}, code=0x{abort_code:08X}"
        )
        self.index = index
        self.subindex = subindex
        self.abort_code = abort_code


class SdoTimeoutError(TimeoutError):
    pass


def encode_nmt(command: NmtCommand, node_id: int = 0) -> CanMessage:
    _validate_node_id(node_id, allow_broadcast=True)
    return CanMessage(arbitration_id=0x000, data=bytes([int(command), node_id]))


def encode_sdo_upload_request(node_id: int, index: int, subindex: int) -> CanMessage:
    _validate_node_id(node_id)
    _validate_index(index)
    _validate_subindex(subindex)
    return CanMessage(
        arbitration_id=0x600 + node_id,
        data=bytes([0x40, index & 0xFF, index >> 8, subindex, 0, 0, 0, 0]),
    )


def encode_sdo_download_request(
    node_id: int,
    index: int,
    subindex: int,
    value: int,
    size: int,
    signed: bool = False,
) -> CanMessage:
    _validate_node_id(node_id)
    _validate_index(index)
    _validate_subindex(subindex)
    if size not in (1, 2, 4):
        raise ValueError("SDO expedited download size must be 1, 2, or 4 bytes")

    command = {1: 0x2F, 2: 0x2B, 4: 0x23}[size]
    payload = int(value).to_bytes(size, byteorder="little", signed=signed)
    return CanMessage(
        arbitration_id=0x600 + node_id,
        data=bytes([command, index & 0xFF, index >> 8, subindex]) + payload.ljust(4, b"\x00"),
    )


def decode_sdo_upload_response(
    message: CanMessage,
    node_id: int,
    index: int,
    subindex: int,
    signed: bool = False,
) -> int:
    _validate_sdo_response_header(message, node_id, index, subindex)
    command = message.data[0]
    if command == 0x80:
        abort_code = int.from_bytes(message.data[4:8], byteorder="little")
        raise SdoAbortError(index, subindex, abort_code)
    if command not in (0x4F, 0x4B, 0x43):
        raise ValueError(f"unsupported SDO upload response command 0x{command:02X}")

    size = {0x4F: 1, 0x4B: 2, 0x43: 4}[command]
    return int.from_bytes(message.data[4 : 4 + size], byteorder="little", signed=signed)


def decode_sdo_download_response(message: CanMessage, node_id: int, index: int, subindex: int) -> None:
    _validate_sdo_response_header(message, node_id, index, subindex)
    command = message.data[0]
    if command == 0x80:
        abort_code = int.from_bytes(message.data[4:8], byteorder="little")
        raise SdoAbortError(index, subindex, abort_code)
    if command != 0x60:
        raise ValueError(f"unsupported SDO download response command 0x{command:02X}")


class CanopenClient:
    def __init__(self, bus: CanBus, node_id: int, timeout: float = 1.0) -> None:
        _validate_node_id(node_id)
        self._bus = bus
        self.node_id = node_id
        self.timeout = timeout

    def send_nmt(self, command: NmtCommand, node_id: int | None = None) -> None:
        target = self.node_id if node_id is None else node_id
        message = encode_nmt(command, target)
        self._bus.send(message.arbitration_id, message.data)

    def send_message(self, message: CanMessage) -> None:
        self._bus.send(message.arbitration_id, message.data)

    def sdo_read(self, index: int, subindex: int = 0, signed: bool = False) -> int:
        request = encode_sdo_upload_request(self.node_id, index, subindex)
        self._bus.send(request.arbitration_id, request.data)
        response = self._recv_sdo_response(index, subindex)
        return decode_sdo_upload_response(response, self.node_id, index, subindex, signed=signed)

    def sdo_write(
        self,
        index: int,
        subindex: int,
        value: int,
        size: int,
        signed: bool = False,
    ) -> None:
        request = encode_sdo_download_request(self.node_id, index, subindex, value, size, signed=signed)
        self._bus.send(request.arbitration_id, request.data)
        response = self._recv_sdo_response(index, subindex)
        decode_sdo_download_response(response, self.node_id, index, subindex)

    def _recv_sdo_response(self, index: int, subindex: int) -> CanMessage:
        expected_id = 0x580 + self.node_id
        deadline = monotonic() + self.timeout
        while monotonic() < deadline:
            remaining = max(0.0, deadline - monotonic())
            message = self._bus.recv(remaining)
            if message is None:
                break
            if message.arbitration_id == expected_id:
                return message
        raise SdoTimeoutError(f"timeout waiting for SDO response 0x{index:04X}:{subindex:02X}")


def _validate_sdo_response_header(message: CanMessage, node_id: int, index: int, subindex: int) -> None:
    _validate_node_id(node_id)
    if message.arbitration_id != 0x580 + node_id:
        raise ValueError("unexpected SDO response arbitration ID")
    if len(message.data) != 8:
        raise ValueError("SDO response must contain 8 data bytes")
    actual_index = message.data[1] | (message.data[2] << 8)
    actual_subindex = message.data[3]
    if actual_index != index or actual_subindex != subindex:
        raise ValueError("unexpected SDO response object index")


def _validate_node_id(node_id: int, allow_broadcast: bool = False) -> None:
    minimum = 0 if allow_broadcast else 1
    if not minimum <= node_id <= 127:
        raise ValueError(f"node_id must be in range {minimum}..127")


def _validate_index(index: int) -> None:
    if not 0 <= index <= 0xFFFF:
        raise ValueError("index must be in range 0x0000..0xFFFF")


def _validate_subindex(subindex: int) -> None:
    if not 0 <= subindex <= 0xFF:
        raise ValueError("subindex must be in range 0x00..0xFF")
