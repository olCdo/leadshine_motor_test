# Development Log

## 2026-06-03

### Completed

- Initialized git repository and configured remote `origin` as `https://github.com/olCdo/leadshine_motor_test.git`.
- Confirmed target project direction:
  - Python program.
  - Ubuntu runtime on Orange Pi 5 Plus.
  - Leadshine LD2-CAN drive.
  - CANopen Profile Velocity Mode.
  - Runtime control through PDO.
  - Single-motor first version.
- Created project governance documents and version-control rules.
- Added `.gitignore` rule to keep local PDF manuals out of git.

### Verification

- Confirmed current repository has no commits yet.
- Confirmed local manual exists at `docs/LD2-CAN系列用户使用手册V2.1.pdf`.
- Confirmed manual PDF is ignored by `.gitignore`.

### Issues / Notes

- No motor-control code has been implemented yet.
- Ubuntu CAN hardware setup for Orange Pi 5 Plus is outside the current repository scope and must be documented or verified before real motor tests.
