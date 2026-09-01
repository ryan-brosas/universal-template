# Agent Rules: global baseline for every CLI

This file is the **global agent ruleset** for `~/.agents`, the shared settings
directory read by every agent CLI on this machine (pi, Claude Code,
Codex/OpenCode, opencode, agy/veda, subprocess agents).

**Project instructions win.** When a repository's own `AGENTS.md` or rules
disagree with anything below, follow the project. This file only sets defaults
that apply everywhere.

## Ground truth

- Source, tests, compiler/runtime behavior, and project requirements outrank
  summaries, graphs, skills, and model opinions.
- Route by need through the owning skills; connected is not mandatory, and no
  fixed retrieval chain runs per task:
  - `skills/evidence-router/`: where evidence comes from
  - `skills/execution-router/`: how work is executed
  - `skills/reference-driven-development/`: outside prior art when it helps
  - `skills/project-bootstrap/`: entering an unfamiliar repository

Evidence paths (`reference/`, `reference/web/`, `foundation-pack/`), MCP
capabilities, and detailed routing live in those skills and in `README.md` /
`references/reference-contract.md`. Do not assume every project uses them.

## Reversible work needs no permission ritual

A coding task inside the current git workspace implies reversible change.
Without asking again, you may: read and search anything; modify tracked
source; create project files; refactor; delete obsolete tracked files when
the task requires it; run builds/tests/linters/formatters; inspect with
`git diff`/`status`/`log`; commit locally per project conventions.

Confirmation (quote the exact command and its blast radius, then wait for the
user in the same session) is for dangerous actions only:

- deleting or overwriting untracked or user data;
- `rm -rf` outside controlled project/temp scope;
- history rewrites: `git reset --hard`, `git clean -fd`, force-push;
- production mutation, credentials/secrets, external side effects with
  real-world consequences;
- machine-wide/system changes not implied by the task.

Never expose, invent, or commit credentials or secret material. Tokens stay
in env vars, referenced only by name.

**Universal execution invariants**: the complete constitution (work
preservation, unrelated-change preservation, additive recovery, artifact
inspection, bounded filesystem discovery, non-interactive safety, external
write boundary, review-thread continuity, commit-convention precedence,
shell-text handling, reversible-operation preference, separator style,
project precedence) lives in `APPEND_SYSTEM.md`. Hosts wired to append it
load all invariants every session; the safety-critical core above is kept
here because not every documented host loads `APPEND_SYSTEM.md` yet. Machine
wiring stays in this file: MCP tokens live in env vars (`~/.profile`,
`~/.dsh/.env`), referenced only by name.

## Finish line

Before claiming completion, run the project's relevant
compiler/tests/lint/verification, inspect the output, and cite the artifact
(command + exit code, file:line, or diff). Pair completion claims with a clean
`git diff --check` on the changed range.

**Working on this repository (`~/.agents`, universal-template)**, run its
catalog verification suite; these are repository-specific checks, not a
universal requirement:

```bash
SKILLS_ROOT="$PWD/skills" python3 scripts/skill-validator.py   # P0 count must be 0
python3 scripts/catalog-quality.py      # structure, visibility, budget, generated-catalog freshness
python3 scripts/repo-hygiene.py
python3 scripts/policy-consistency.py
python3 scripts/style-lint.py --selftest   # style fixtures must pass
python3 scripts/style-lint.py              # hard rules on the default docs scope
python3 scripts/web-reference-manifest.py --selftest   # web reference fixtures must pass
python3 scripts/dead-code.py
python3 scripts/foundation-validator.py
python3 scripts/reference-retrieval-fixture.py --selftest
python3 scripts/skill-catalog.py --selftest
CHECK_RANGE="origin/main..HEAD" python3 scripts/conventional-commit.py
git diff --check
```

CI (`.github/workflows/pr-quality.yml`) enforces the same suite on push and
pull_request. `python3 scripts/policy-consistency.py --selftest` and
`python3 scripts/legacy-skill-report.py` are extra advisory tools outside the
required suite: the selftest is a regression fixture, and the legacy report is
a migration queue, not a gate.

## Entry architecture

The normal loop is: task → inspect current code/evidence → implement → run
relevant verification → finish. No lifecycle machinery is required for
ordinary work.

Entry skills, each earning its own trigger:

- `project-bootstrap`: entering an unfamiliar repository (read-only
  onboarding by default), greenfield setup, or intentional lightweight
  project governance. Idempotent; never generates default host artifact packs
  or a user profile. Host runtime config (for pi: `~/.pi/` and project
  `.pi/` when the project uses it) is outside this global tree.
- `brainstorming`: ambiguous direction: ground in the repo, frame, explore
  real alternatives, decide. No planning files by default.
- `goal-setup`: durable execution contract for significant/multi-session
  work: ONE goal artifact with verifiable done-criteria.
- `prototype`: cheap runnable learning; verification follows the question.
- `leverage-capture`: post-work classification (code/reference/gate/skill/
  memory/not-worth-saving); capture is threshold-driven, never automatic.

Persistent project artifacts need a promotion test: only intent, decisions,
constraints, and traps that are expensive to reconstruct from source, Git,
manifests, or CI. The session is the artifact for ordinary work.

## Writing style (natural-language output)

Write plain technical English in prose you author: active voice, concrete
verbs, short clear sentences, short paragraphs. Avoid em dashes, filler
intensifiers (`genuinely`, `really`, `truly`, `actually`), vague corporate wording,
heavy noun stacks, and repetitive rhetorical structures. Keep the voice
natural for speech. Preserve exact code, commands, identifiers, quotes, logs,
citations, source text, and machine formats. Detailed rules and the
deterministic linter live in `skills/house-writing-style/` and
`scripts/style-lint.py`.

## Conventions (defaults; the project wins)

- Branches: at most three hyphen-separated lowercase words, no slashes, no
  type prefixes; `main` is the long-lived branch.
- Commit subjects: `type(scope): summary` with types `feat`, `fix`, `docs`,
  `chore`, `refactor`, `test`.
- `~/.agents` stays a configuration/skill surface: no package manifests or
  dependency trees; no system rebuilds or installs unless asked.

## Global layout & host wiring (facts)

Layout, policy owners, and MCP registry: `README.md`. Host mounts: pi reads
`~/.agents/skills` natively; Claude Code (`~/.claude/skills`,
`~/.claude/CLAUDE.md`), DSH (`~/.dsh/skills`), Codex (`~/.codex/skills`,
`~/.codex/AGENTS.md`), OpenCode (`~/.config/opencode/skills`,
`~/.config/opencode/AGENTS.md`), and Gemini CLI (`~/.gemini/GEMINI.md`) read
this tree via symlinks/additive merges.
