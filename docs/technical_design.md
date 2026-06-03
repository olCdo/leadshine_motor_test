# Technical Design

## Architecture

The program should be organized as a small Python CLI application with clear boundaries:

- CLI command loop.
- Configuration and safety limits.
- CANopen transport.
- PDO mapping and payload encoding.
- Drive state and telemetry decoding.
- CSV logging.

The first implementation should avoid broad abstractions. Keep the code small and direct until real hardware behavior is verified.

## CANopen Strategy

Use SocketCAN on Ubuntu through `python-can`.

The program does not depend on an EDS file in the first version. It uses known object dictionary entries from the Leadshine LD2-CAN manual.

SDO is allowed only during startup and setup. Runtime control and telemetry should use PDO.

## Startup Flow

1. Open CAN interface.
2. Send NMT reset/start sequence as needed.
3. Enter Pre-operational state for PDO configuration.
4. Configure RPDO and TPDO mappings through SDO.
5. Set Profile Velocity Mode with `6060 = 3`.
6. Set acceleration and deceleration parameters.
7. Enter Operational state.
8. Start CLI command loop and telemetry handling.

## Runtime PDO Design

### RPDO

RPDO should carry:

- `6040` control word.
- `60FF` target velocity.

The CLI accepts rpm. The driver object uses pulse/s, so convert with:

```text
pulse_per_second = rpm * pulses_per_rev / 60
```

Default `pulses_per_rev` is `10000`.

### TPDO

TPDO should return:

- `6041` status word.
- `606C` actual velocity.
- Bus voltage.
- Temperature.
- Actual torque percent.

If the drive cannot map every desired feedback item into the selected TPDO layout, keep speed and status word as mandatory and document any missing telemetry in the development log.

## Important Object Dictionary Entries

- `6040`: control word.
- `6041`: status word.
- `6060`: operation mode.
- `6061`: operation mode display.
- `606C`: actual velocity.
- `6077`: actual torque.
- `6079`: bus voltage.
- `6083`: profile acceleration.
- `6084`: profile deceleration.
- `60FF`: target velocity.
- `5501:04`: actual torque monitor, alternative percent-style load reference.
- `5502:06`: temperature monitor.

## Error Handling

- Treat SDO timeout as startup failure.
- Treat missing TPDO updates as communication loss.
- When fault bit is present in `6041`, stop accepting non-zero speed commands.
- Do not automatically reset faults.
- Log all communication and drive-state errors.
