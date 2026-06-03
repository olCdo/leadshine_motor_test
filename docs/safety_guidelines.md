# Safety Guidelines

## Default Safety Policy

The first version is a test tool, not a production motion controller. It must prefer conservative behavior.

Defaults:

- Max speed: 500 rpm.
- Acceleration: 500 rpm/s.
- Deceleration: 500 rpm/s.
- Single motor only.
- No automatic fault reset.
- No persistent drive parameter saving.

## Command Safety

- Reject non-zero speed commands when the drive reports a fault.
- Reject speeds whose absolute value is greater than the configured max rpm.
- `stop` must command zero target speed.
- `disable` must command zero target speed before disabling.
- `quit`, Ctrl+C, and unexpected exceptions should attempt:
  1. Command zero target speed.
  2. Wait briefly.
  3. Disable the drive.

## Fault Handling

When the drive reports a fault:

- Do not automatically reset it.
- Stop accepting non-zero speed commands.
- Display the fault state clearly in the CLI.
- Record the fault state in CSV logs.

Fault reset may be added later only as an explicit manual command after the test workflow is reviewed.

## External Safety

The first version does not manage external emergency stop, limit, or brake IO.

The test bench must provide appropriate physical safety measures before motor movement:

- Secure motor mounting.
- Safe load or no-load condition.
- Accessible emergency stop.
- Correct wiring and grounding.
- Correct CAN termination and bitrate.

## Parameter Safety

Do not save parameters permanently to the drive in the first version.

PDO mappings and runtime parameters should be configured temporarily at startup so the drive can return to its previous persistent configuration after power cycling.
