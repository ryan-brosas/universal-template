# Contributing

Repository-specific checks for `~/.agents` (universal-template). They are not
universal requirements for other projects.

## Before pushing

Run the catalog verification suite (same as CI `quality / required`):

```bash
SKILLS_ROOT="$PWD/skills" python3 scripts/skill-validator.py   # P0 count must be 0
python3 scripts/install-prompts.py --check-repo
python3 scripts/install-prompts.py --selftest
python3 scripts/render-prompt.py --selftest
python3 scripts/catalog-quality.py --selftest
python3 scripts/catalog-quality.py
python3 scripts/repo-hygiene.py
python3 scripts/policy-consistency.py
python3 scripts/style-lint.py --selftest
python3 scripts/style-lint.py
python3 scripts/web-reference-manifest.py --selftest
python3 scripts/dead-code.py
python3 scripts/foundation-validator.py --selftest
python3 scripts/foundation-validator.py
python3 scripts/reference-retrieval-fixture.py --selftest
CHECK_RANGE="origin/main..HEAD" python3 scripts/conventional-commit.py
git diff --check
```

Advisory only (not CI-gated): `python3 scripts/policy-consistency.py --selftest`,
`python3 scripts/legacy-skill-report.py`.

## Pull requests

- Small, focused PRs against `main` with a conventional title
  (`feat(scope): ...`); the `pr-title` check enforces it, and the same parser
  (`scripts/pr-metadata.py`) derives the `type:*` and `breaking-change`
  labels, so do not hand-add those.
- `area:*` labels apply automatically from changed paths.
- The PR body must follow `.github/pull_request_template.md`; only claims you
  actually verified.
- Required checks: `quality / required` and `pr-title` (default-branch
  ruleset).

## Skills

New or changed `SKILL.md` files follow the one grammar in
`skills/writing-skills/SKILL.md`; the catalog gates must pass.
