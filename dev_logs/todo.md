# Todo

## Next Development Steps

1. Create Python project skeleton.
   - Package structure.
   - CLI entry point.
   - Dependency declaration.
   - Basic configuration loading.
   - No real CAN control in this step.

2. Implement CANopen base communication.
   - SocketCAN bus open.
   - NMT reset/start commands.
   - Expedited SDO read/write.
   - Basic timeout and error handling.

3. Implement PDO configuration and encoding.
   - Temporary RPDO/TPDO mapping at startup.
   - RPDO payload encoder.
   - TPDO payload decoder.
   - Unit tests for payload layout.

4. Implement velocity-mode control.
   - `enable`
   - `disable`
   - `speed <rpm>`
   - `stop`
   - Conservative speed and acceleration limits.

5. Implement monitoring and CSV logging.
   - Status word parsing.
   - Actual speed.
   - Bus voltage.
   - Temperature.
   - Actual torque percent as load reference.
   - Periodic CSV log output.

## Current Blockers

- Real Ubuntu CAN interface name, bitrate, and node ID must be confirmed on the Orange Pi test setup before hardware testing.
- Exact TPDO mapping support for all desired monitoring objects must be confirmed on the drive during integration.

## Deferred

- Multi-motor control.
- Web UI.
- Windows mock mode.
- Persistent drive parameter saving.
- External emergency stop, limit, or brake IO integration.
