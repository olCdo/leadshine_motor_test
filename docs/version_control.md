# Version Control

## Branch

Use the current `master` branch unless the user explicitly requests a different default branch.

## Remote

Remote repository:

```text
https://github.com/olCdo/leadshine_motor_test.git
```

## Commit Scope

Use small commits. Each commit should correspond to one development step.

Recommended first commit:

```text
chore: add project standards and development logs
```

The first commit should include only:

- `AGENTS.md`
- `.gitignore`
- `docs/*.md`
- `dev_logs/*.md`

## Ignore Rules

Do not commit:

- `docs/*.pdf`
- Python cache files.
- Virtual environments.
- Runtime logs.
- CSV test output.
- Local editor files.

Do commit:

- Markdown project standards.
- Development logs.
- Source code.
- Tests.
- Dependency files.

## Pre-commit Checklist

Before each commit:

1. Run relevant verification.
2. Update `dev_logs/development_log.md`.
3. Update `dev_logs/todo.md`.
4. Run `git status --short`.
5. Confirm ignored local files are not staged.
