from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from .canopen import CanMessage
from .pdo import rpm_to_pulse_per_second


SDO_ABORT_OBJECT_NOT_FOUND = 0x06020000


@dataclass
class ObjectValue:
    value: int
    size: int


class SimulatedCanBus:
    """Minimal CANopen drive simulator for local CLI validation."""

    def __init__(self, node_id: int = 1, pulses_per_rev: int = 10_000) -> None:
        self.node_id = node_id
        self.pulses_per_rev = pulses_per_rev
        self.sent: list[tuple[int, bytes]] = []
        self._responses: deque[CanMessage] = deque()
        self._objects: dict[tuple[int, int], ObjectValue] = {}
        self._nmt_operational = False
        self._init_objects()

    def send(self, arbitration_id: int, data: bytes) -> None:
        self.sent.append((arbitration_id, data))
        if arbitration_id == 0x000 and len(data) >= 2:
            self._handle_nmt(data)
            return
        if arbitration_id == 0x600 + self.node_id and len(data) == 8:
            self._handle_sdo(data)
            return
        if arbitration_id == 0x200 + self.node_id and len(data) >= 6:
            self._handle_rpdo1(data)

    def recv(self, timeout: float | None = None) -> CanMessage | None:
        if self._responses:
            return self._responses.popleft()
        if self._nmt_operational:
            return self._make_tpdo1()
        return None

    def shutdown(self) -> None:
        return None

    def __enter__(self) -> SimulatedCanBus:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.shutdown()

    def _init_objects(self) -> None:
        self._set(0x6041, 0x00, 0x0650, 2)
        self._set(0x6060, 0x00, 0, 1)
        self._set(0x6061, 0x00, 0, 1)
        self._set(0x606C, 0x00, 0, 4)
        self._set(0x6077, 0x00, 0, 2)
        self._set(0x6078, 0x00, 0, 2)
        self._set(0x6079, 0x00, 23700, 4)
        self._set(0x6083, 0x00, rpm_to_pulse_per_second(500, self.pulses_per_rev), 4)
        self._set(0x6084, 0x00, rpm_to_pulse_per_second(500, self.pulses_per_rev), 4)
        self._set(0x60FF, 0x00, 0, 4)

    def _handle_nmt(self, data: bytes) -> None:
        command = data[0]
        target = data[1]
        if target not in (0, self.node_id):
            return
        if command == 0x01:
            self._nmt_operational = True
            self._set(0x6061, 0x00, self._get(0x6060, 0x00), 1)
        elif command == 0x80:
            self._nmt_operational = False

    def _handle_sdo(self, data: bytes) -> None:
        command = data[0]
        index = data[1] | (data[2] << 8)
        subindex = data[3]
        if command == 0x40:
            self._enqueue_sdo_upload(index, subindex)
            return
        if command in (0x2F, 0x2B, 0x23):
            size = {0x2F: 1, 0x2B: 2, 0x23: 4}[command]
            value = int.from_bytes(
                data[4 : 4 + size],
                byteorder="little",
                signed=_is_signed_object(index),
            )
            self._set(index, subindex, value, size)
            if index == 0x6060 and subindex == 0:
                self._set(0x6061, 0x00, value, 1)
            if index == 0x60FF and subindex == 0:
                self._set(0x606C, 0x00, value, 4)
            self._responses.append(
                CanMessage(
                    arbitration_id=0x580 + self.node_id,
                    data=bytes([0x60, index & 0xFF, index >> 8, subindex, 0, 0, 0, 0]),
                )
            )
            return
        self._enqueue_abort(index, subindex)

    def _handle_rpdo1(self, data: bytes) -> None:
        control_word = int.from_bytes(data[0:2], byteorder="little", signed=False)
        target_velocity = int.from_bytes(data[2:6], byteorder="little", signed=True)
        if control_word == 0x0006:
            self._set(0x6041, 0x00, 0x4631 if self._nmt_operational else 0x0631, 2)
            self._set(0x606C, 0x00, 0, 4)
        elif control_word == 0x0007:
            self._set(0x6041, 0x00, 0x4633 if self._nmt_operational else 0x0633, 2)
            self._set(0x606C, 0x00, 0, 4)
        elif control_word == 0x000F:
            self._set(0x6041, 0x00, 0x5237 if self._nmt_operational else 0x0627, 2)
            self._set(0x60FF, 0x00, target_velocity, 4)
            self._set(0x606C, 0x00, target_velocity, 4)
            load = min(1000, abs(target_velocity) // 100)
            self._set(0x6077, 0x00, load, 2)
            self._set(0x6078, 0x00, load // 2, 2)

    def _enqueue_sdo_upload(self, index: int, subindex: int) -> None:
        obj = self._objects.get((index, subindex))
        if obj is None:
            self._enqueue_abort(index, subindex)
            return
        command = {1: 0x4F, 2: 0x4B, 4: 0x43}[obj.size]
        payload = int(obj.value).to_bytes(obj.size, byteorder="little", signed=obj.value < 0)
        self._responses.append(
            CanMessage(
                arbitration_id=0x580 + self.node_id,
                data=bytes([command, index & 0xFF, index >> 8, subindex]) + payload.ljust(4, b"\x00"),
            )
        )

    def _enqueue_abort(self, index: int, subindex: int) -> None:
        self._responses.append(
            CanMessage(
                arbitration_id=0x580 + self.node_id,
                data=bytes([0x80, index & 0xFF, index >> 8, subindex])
                + SDO_ABORT_OBJECT_NOT_FOUND.to_bytes(4, byteorder="little"),
            )
        )

    def _set(self, index: int, subindex: int, value: int, size: int) -> None:
        self._objects[(index, subindex)] = ObjectValue(value=value, size=size)

    def _get(self, index: int, subindex: int) -> int:
        return self._objects[(index, subindex)].value

    def _make_tpdo1(self) -> CanMessage:
        status_word = self._get(0x6041, 0x00)
        actual_velocity = self._get(0x606C, 0x00)
        data = status_word.to_bytes(2, byteorder="little", signed=False)
        data += actual_velocity.to_bytes(4, byteorder="little", signed=True)
        return CanMessage(arbitration_id=0x180 + self.node_id, data=data)


def _is_signed_object(index: int) -> bool:
    return index in {0x6060, 0x6061, 0x606C, 0x6077, 0x6078, 0x60FF}
