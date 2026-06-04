from __future__ import annotations

from dataclasses import dataclass
from time import sleep

from .canopen import CanopenClient
from .drive import (
    ControlWord,
    StatusWord,
    VelocityCommand,
    VelocityModePreparation,
    build_velocity_command,
    prepare_velocity_mode,
)
from .telemetry import DriveStatusSnapshot, read_drive_status


@dataclass
class MotorController:
    client: CanopenClient
    max_rpm: int
    accel_rpm_s: int
    decel_rpm_s: int
    pulses_per_rev: int
    prepared: VelocityModePreparation | None = None
    enabled: bool = False
    current_target_rpm: float = 0.0

    def prepare(self) -> VelocityModePreparation:
        self.prepared = prepare_velocity_mode(
            self.client,
            accel_rpm_s=self.accel_rpm_s,
            decel_rpm_s=self.decel_rpm_s,
            pulses_per_rev=self.pulses_per_rev,
        )
        if not self.prepared.display_matches:
            raise ValueError("operation mode display is not Profile Velocity Mode")
        return self.prepared

    def enable(self) -> StatusWord:
        self._ensure_prepared()
        self._send_control(0, int(ControlWord.SHUTDOWN))
        sleep(0.1)
        self._send_control(0, int(ControlWord.SWITCH_ON))
        sleep(0.1)
        self._send_control(0, int(ControlWord.ENABLE_OPERATION))
        sleep(0.2)
        status = self._read_status()
        if not status.operation_enabled:
            raise ValueError("drive did not reach operation_enabled")
        self.enabled = True
        return status

    def set_speed(self, rpm: float) -> VelocityCommand:
        if not self.enabled:
            raise ValueError("drive must be enabled before setting speed")
        command = build_velocity_command(
            node_id=self.client.node_id,
            control_word=int(ControlWord.ENABLE_OPERATION),
            target_rpm=rpm,
            max_rpm=self.max_rpm,
            pulses_per_rev=self.pulses_per_rev,
        )
        self.client.send_message(command.frame)
        self.current_target_rpm = rpm
        return command

    def stop(self) -> StatusWord:
        if self.enabled:
            self._send_control(0, int(ControlWord.ENABLE_OPERATION))
            sleep(self._stop_wait_seconds())
            self.current_target_rpm = 0.0
        return self._read_status()

    def disable(self) -> StatusWord:
        if self.enabled:
            self.stop()
            self._send_control(0, int(ControlWord.DISABLE_OPERATION))
            sleep(0.1)
            self._send_control(0, int(ControlWord.SHUTDOWN))
            sleep(0.1)
            self.enabled = False
        return self._read_status()

    def status(self) -> DriveStatusSnapshot:
        return read_drive_status(self.client, pulses_per_rev=self.pulses_per_rev)

    def safe_shutdown(self) -> None:
        try:
            self.disable()
        except Exception:
            try:
                self._send_control(0, int(ControlWord.DISABLE_OPERATION))
                sleep(0.1)
                self._send_control(0, int(ControlWord.SHUTDOWN))
            except Exception:
                pass

    def _ensure_prepared(self) -> None:
        if self.prepared is None:
            self.prepare()

    def _read_status(self) -> StatusWord:
        return StatusWord(self.client.sdo_read(0x6041, 0x00))

    def _send_control(self, rpm: float, control_word: int) -> None:
        command = build_velocity_command(
            node_id=self.client.node_id,
            control_word=control_word,
            target_rpm=rpm,
            max_rpm=self.max_rpm,
            pulses_per_rev=self.pulses_per_rev,
        )
        self.client.send_message(command.frame)

    def _stop_wait_seconds(self) -> float:
        if self.decel_rpm_s <= 0:
            return 0.5
        return min(2.0, max(0.3, abs(self.current_target_rpm) / self.decel_rpm_s + 0.2))
