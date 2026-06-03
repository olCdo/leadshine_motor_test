# Development Process

## Development Rhythm

Develop in small, verifiable steps. Each step should have one purpose and one commit.

Before changing code:

1. Read `AGENTS.md`.
2. Read the relevant standard documents in `docs/`.
3. Review `dev_logs/todo.md`.
4. Add or update the todo entry for the current step.

After changing code or documents:

1. Run the relevant verification command.
2. Update `dev_logs/development_log.md` with:
   - What changed.
   - What was verified.
   - What failed or remains uncertain.
3. Update `dev_logs/todo.md`.
4. Check `git status`.
5. Commit only the completed step.

## Planned Development Steps

1. Project governance files.
2. Python project skeleton.
3. CANopen base communication.
4. PDO configuration and payload encoding.
5. Velocity-mode control.
6. Telemetry monitoring and CSV logging.

Do not combine these steps unless the user explicitly asks for it.

## Verification Expectations

- Documentation-only changes:
  - Check `git status`.
  - Confirm ignored files stay ignored.
- Python skeleton:
  - Run import checks.
  - Run CLI help.
- Communication layer:
  - Run unit tests for message encoding.
  - Run non-motion hardware communication checks when hardware is available.
- Motor-control changes:
  - Run unit tests.
  - Verify speed limits before any real motor movement.
  - Test low rpm first.

## Logging Standard

Each log entry should include:

- Date.
- Completed items.
- Verification.
- Issues or notes.

Keep the log factual. Do not remove old entries unless correcting a clear mistake.
