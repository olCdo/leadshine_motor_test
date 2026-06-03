from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    """Runtime defaults for the motor test CLI.

    The current skeleton only stores configuration. CAN hardware access will be
    added in a later development step.
    """

    interface: str = "can0"
    bitrate: int = 1_000_000
    node_id: int = 1
    max_rpm: int = 500
    accel_rpm_s: int = 500
    decel_rpm_s: int = 500
    pulses_per_rev: int = 10_000
    log_dir: str = "logs"

    def validate(self) -> None:
        if not self.interface:
            raise ValueError("interface must not be empty")
        if not 1 <= self.node_id <= 127:
            raise ValueError("node_id must be in range 1..127")
        if self.bitrate <= 0:
            raise ValueError("bitrate must be positive")
        if self.max_rpm <= 0:
            raise ValueError("max_rpm must be positive")
        if self.accel_rpm_s <= 0:
            raise ValueError("accel_rpm_s must be positive")
        if self.decel_rpm_s <= 0:
            raise ValueError("decel_rpm_s must be positive")
        if self.pulses_per_rev <= 0:
            raise ValueError("pulses_per_rev must be positive")
