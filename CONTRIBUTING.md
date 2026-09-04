# Contributing

Repository-specific checks for `~/.agents` (universal-template). They are not
universal requirements for other projects. Ordinary use of the baseline does
not require Python.

## Responsibility boundary

Models review policy meaning, prose quality, skill relevance and overlap, model
choice, evidence sufficiency, and engineering tradeoffs. Source, Git, host
inventories, tests, and runtime output supply current facts. Required checks are
limited to answers that follow exactly from bytes or filesystem state.

Use the hidden `template-maintenance` skill for semantic review. It selects only
the checks relevant to the change and reports judgment calls separately from
hard failures.

## Before pushing

Maintainers need Python only for the current deterministic publication helpers.
Run the consolidated contract suite used by CI:

```bash
SKILLS_ROOT="$PWD/skills" python3 scripts/skill-validator.py
python3 scripts/install-prompts.py --check-repo
python3 scripts/install-prompts.py --selftest
python3 scripts/render-prompt.py --selftest
python3 scripts/skill-catalog.py generate --check
python3 scripts/repo-hygiene.py
python3 scripts/web-reference-manifest.py --selftest
python3 scripts/pr-metadata.py --selftest
git diff --check
```

These commands check metadata, names, references, structured-data parsing,
required paths, portable MCP declarations, secret patterns, generated parity,
prompt-adapter mutation safety, title protocol parsing, and changed-line
whitespace. They do not approve policy, prose, routing, or usefulness.

## Tool classification

| Classification | Scripts | Ownership |
| --- | --- | --- |
| REQUIRED HARD CONTRACT | `skill-validator.py`, `repo-hygiene.py`, `web-reference-manifest.py`, `pr-metadata.py` | Exact metadata, files, paths, schemas, secrets, and automation protocols. |
| OPTIONAL COMPATIBILITY TOOL | `install-prompts.py`, `render-prompt.py` | Legacy host installation and prompt rendering; never canonical. |
| OPTIONAL DIAGNOSTIC | `github-audit.py`, `runtime-capabilities.py` | Read-only environment reports; current native output remains authoritative. |
| GENERATED-ARTIFACT TOOL | `skill-catalog.py` | Derives the optional human catalog from skill frontmatter. |

See `docs/maintainer-tooling.md` for retired-script rationale.

## Pull requests

- Use small PRs against `main` with a conventional title such as
  `refactor(core): make the template model-first and runtime-independent`.
  The exact title protocol drives release labels.
- `area:*` and `type:*` labels are derived automatically.
- Follow `.github/pull_request_template.md` and report only verification that
  actually ran.
- Required checks are `quality / required` and `pr-title`.

## Skills

Every active `skills/<name>/SKILL.md` has local `invocation` metadata. The
`name` equals the directory, references resolve within the skill, and host
visibility remains expressed by `disable-model-invocation`. The model owns the
classification decision; the validator checks only the resulting exact contract.
