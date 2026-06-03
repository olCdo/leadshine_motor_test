from __future__ import annotations

from .canopen import CanMessage


class SocketCanError(RuntimeError):
    pass


class SocketCanBus:
    """SocketCAN adapter backed by python-can."""

    def __init__(self, interface: str) -> None:
        try:
            import can
        except ImportError as exc:
            raise SocketCanError(
                "python-can is required for SocketCAN. Install it with: "
                "python3 -m pip install -r requirements.txt"
            ) from exc

        self.interface = interface
        try:
            self._bus = can.Bus(interface="socketcan", channel=interface, receive_own_messages=False)
        except Exception as exc:  # python-can raises backend-specific exceptions.
            raise SocketCanError(f"failed to open SocketCAN interface {interface!r}: {exc}") from exc

    def send(self, arbitration_id: int, data: bytes) -> None:
        import can

        message = can.Message(
            arbitration_id=arbitration_id,
            data=data,
            is_extended_id=False,
        )
        try:
            self._bus.send(message)
        except Exception as exc:
            raise SocketCanError(f"failed to send CAN frame on {self.interface!r}: {exc}") from exc

    def recv(self, timeout: float | None = None) -> CanMessage | None:
        try:
            message = self._bus.recv(timeout=timeout)
        except Exception as exc:
            raise SocketCanError(f"failed to receive CAN frame on {self.interface!r}: {exc}") from exc
        if message is None:
            return None
        return CanMessage(arbitration_id=message.arbitration_id, data=bytes(message.data))

    def shutdown(self) -> None:
        self._bus.shutdown()

    def __enter__(self) -> SocketCanBus:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.shutdown()
