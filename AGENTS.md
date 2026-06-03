# AGENTS.md

## Project Purpose

This project is a Python-based motor test tool for Leadshine LD2-CAN servo drives. The target runtime is Ubuntu on Orange Pi 5 Plus. Windows is used only for code editing and project maintenance.

The first implementation target is a safe command-line test program that controls one motor through CANopen PDO in Profile Velocity Mode.

## Required Reading Before Development

Read these files before making project changes:

- `docs/requirements.md`
- `docs/technical_design.md`
- `docs/safety_guidelines.md`
- `docs/development_process.md`
- `docs/version_control.md`

Use the local PDF manual in `docs/` only as a reference. PDF manuals are ignored by git and must not be committed.

## Development Log Requirements

Every development step must update:

- `dev_logs/development_log.md`: completed work, verification results, and issues found.
- `dev_logs/todo.md`: current next steps, priorities, blockers, and deferred work.

Do not make large batches of unrelated changes. Each development step should be small, testable, and independently commit-ready.

## Safety Requirements

Motor-control code must follow `docs/safety_guidelines.md`. In particular:

- Keep conservative speed and acceleration defaults.
- Reject speed commands above the configured limit.
- On quit, Ctrl+C, or error, command zero speed before disabling the drive.
- Do not automatically reset drive faults.
- Do not permanently save drive parameters unless a future requirement explicitly allows it.

## Version Control Rules

Follow `docs/version_control.md`.

The first commit should include only project governance files:

- `AGENTS.md`
- `.gitignore`
- `docs/*.md`
- `dev_logs/*.md`

Do not commit `docs/*.pdf`, runtime logs, generated CSV data, virtual environments, or Python cache files.
