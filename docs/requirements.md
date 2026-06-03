# Requirements

## Goal

Build a safe Python command-line motor test program for a Leadshine LD2-CAN servo drive.

The program will run on Ubuntu on Orange Pi 5 Plus and control one motor through CANopen PDO in Profile Velocity Mode.

## Confirmed Requirements

- Language: Python.
- Runtime OS: Ubuntu.
- Development OS: Windows is allowed for editing only.
- Hardware target: Orange Pi 5 Plus connected to a Leadshine LD2-CAN drive.
- Communication: CANopen over SocketCAN.
- Control mode: Profile Velocity Mode.
- Runtime control must use PDO:
  - Set target speed in rpm.
  - Enable the drive.
  - Disable the drive.
  - Stop the motor.
- Runtime feedback must use PDO:
  - Actual speed in rpm.
  - Bus voltage.
  - Actual torque percent as load/current reference.
  - Enable state.
  - Fault state.
  - Temperature.
- SDO may be used during startup for:
  - Temporary PDO mapping configuration.
  - Operation mode setup.
  - Acceleration and deceleration setup.
  - Basic startup checks.
- CSV logging should be enabled by default during tests.

## First Version Scope

- Single motor only.
- CLI interaction only.
- Real hardware only.
- Conservative defaults:
  - Max speed: 500 rpm.
  - Acceleration: 500 rpm/s.
  - Deceleration: 500 rpm/s.
  - Pulses per revolution: 10000.
- Default CAN settings:
  - Interface: `can0`.
  - Bitrate: `1000000`.
  - Node ID: `1`.

## Out of Scope for First Version

- Multi-motor control.
- Synchronized multi-axis control.
- Web UI.
- Windows local mock mode.
- Persistent saving of drive parameters.
- Automatic drive fault reset.
- Direct management of external emergency stop, limit, or brake IO.

## CLI Commands

The first CLI version should provide:

- `enable`
- `disable`
- `speed <rpm>`
- `stop`
- `status`
- `watch [interval_seconds]`
- `quit`
- `help`
