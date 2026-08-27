## Summary

<!-- one or two lines that state the user-visible result -->

## Changed files

- `path`: what changed and why

## Screenshots

No visual result.

## Verification

- `SKILLS_ROOT="$PWD/skills" python3 scripts/skill-validator.py` - pass or fail; exit N
- `python3 scripts/catalog-integrity.py` - pass or fail; exit N
- `python3 scripts/catalog-quality.py` - pass or fail; exit N
- `python3 scripts/repo-hygiene.py` - pass or fail; exit N
- `python3 scripts/dead-code.py` - pass or fail; exit N
- `CHECK_RANGE=origin/main..HEAD python3 scripts/conventional-commit.py` - pass or fail; exit N
- `git diff --check` - pass or fail; exit N

## CI state

- Workflow: Project quality
- Run: pending
- Head commit: pending
- State: pending

## Codebase observation

- Project: None
- Coverage: pending or skipped reason
- Observation: one verified blast-radius statement or skipped reason

## GitHub metadata

- Labels: None
- Milestone: None
- Assignees: None
- Reviewers: None
- Project: None
- State: draft or ready
- Base: main

## Notes for the reviewer

None
