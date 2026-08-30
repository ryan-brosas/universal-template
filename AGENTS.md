# Agent Rules — global baseline for every CLI

This file is the **global agent ruleset** for `~/.agents`, the shared settings
directory read by every agent CLI on this machine (pi, Claude Code,
Codex/OpenCode, opencode, agy/veda, subprocess agents).

**Project instructions win.** When a repository's own `AGENTS.md` or rules
disagree with anything below, follow the project. This file only sets defaults
that apply everywhere.

## Ground truth & routing

- Source, tests, compiler/runtime behavior, and project requirements outrank
  summaries, graphs, skills, and model opinions. Graphs and corpora are
  navigation indexes, not source of truth — confirm cited code in real source.
- Route by need to the smallest capability that closes the gap
  (`skills/evidence-router/`); connected is not mandatory, and no fixed
  retrieval chain runs per task:
  - **Fovea** — active working-set map of the current project (orientation,
    feature location, impact/blast radius); then read exact source.
  - **MCP Steroid / JetBrains** — exact semantic/type/call information,
    inspections, debugger; semantic quality barrier for non-trivial changes.
  - **Fabric** — execution and orchestration: `fabric_exec`, `/fabric
    prewalk` (its real Fabric meaning only), agents/Veda runner when the
    task benefits, Schema audit (observes) / enforce (intentionally strict)
    when selected.
  - **Codebase Memory** — persistent cross-repo structural library (cold path).
  - **OpenViking** — durable experience/context: decisions, failed attempts,
    lessons; not a second copy of local source.
  - **Veda** — the broad model/backend routing layer (alternate provider or
    stronger model when justified). Route by role and capability through
    `skills/effort-router` + `skills/model-router`; discover models at
    runtime, never hard-code them.
- Reusable prior art lives in `<project>/reference/<repo>/` (read-only
  checkout; read source and tests) — not automatically a skill, index, or
  corpus. This repo's global `references/` means contract docs; keep the two
  apart.

## Reversible work needs no permission ritual

A coding task inside the current git workspace implies reversible change.
Without asking again, you may: read and search anything; modify tracked
source; create project files; refactor; delete obsolete tracked files when
the task requires it; run builds/tests/linters/formatters; inspect with
`git diff`/`status`/`log`; commit locally per project conventions.

Confirmation (quote the exact command and its blast radius, then wait for the
user in the same session) is for genuinely dangerous actions only:

- deleting or overwriting untracked or user data;
- `rm -rf` outside controlled project/temp scope;
- history rewrites: `git reset --hard`, `git clean -fd`, force-push;
- production mutation, credentials/secrets, external side effects with
  real-world consequences;
- machine-wide/system changes not implied by the task.

Never expose, invent, or commit credentials or secret material. Tokens stay
in env vars, referenced only by name.

## Finish line

Before claiming completion, run the project's relevant
compiler/tests/lint/verification, inspect the output, and cite the artifact
(command + exit code, file:line, or diff). Pair completion claims with a clean
`git diff --check` on the changed range.

**Working on this repository (`~/.agents`, universal-template)**, run its
catalog verification suite — these are repository-specific checks, not a
universal requirement:

```bash
SKILLS_ROOT="$PWD/skills" python3 scripts/skill-validator.py   # P0 count must be 0
python3 scripts/catalog-integrity.py
python3 scripts/catalog-quality.py
python3 scripts/repo-hygiene.py
python3 scripts/policy-consistency.py
python3 scripts/dead-code.py
CHECK_RANGE="origin/main..HEAD" python3 scripts/conventional-commit.py
git diff --check
```

CI (`.github/workflows/pr-quality.yml`) enforces the same suite on push and
pull_request.

## Pi Fabric: runtime features stay runtime features

- `fabric_exec`, `/fabric prewalk`, Schema, agents, providers are Pi Fabric
  runtime mechanisms. Verify their behavior against the installed pi-fabric
  docs (`docs/agents.md`, `docs/schema-enforcement.md`) before writing policy
  about them.
- **Prewalk** means only the Pi Fabric runtime feature: `/fabric prewalk`
  arms a continuation at a successful monitored mutation boundary and
  continues execution with the configured executor model. It adds no
  system-prompt instruction. Never use "prewalk" for repository exploration
  (the word belongs to Pi Fabric) —
  say discovery, graph discovery, source inspection, or evidence discovery.
- **Schema** modes are `off` (default) / `audit` / `enforce`. In `off`/`audit`
  the `schema.*` loop is available but does not gate direct
  `pi.edit`/`pi.write`/`pi.bash`. Use the Schema loop only when the session
  runs enforce mode, the user invokes a Fabric Schema mechanism, or the task
  explicitly needs transactional/postcondition guarantees. Enforce mode blocks
  direct mutations and disables Fabric Prewalk — do not activate it silently as a
  universal prerequisite.

## Workflow-lifecycle is opt-in

The normal loop is: task → inspect current code/evidence → implement → run
relevant verification → finish. No lifecycle artifacts are required.

`skills/workflow-lifecycle/` serves explicit governance work: workspace
initialization, long-running/multi-session context, lesson capture
(`learn`), cross-cutting audits, pre-claim verification, workspace GC.

`.pi/` artifacts (`project.md`, `tech-stack.md`, `roadmap.md`, `state.md`,
`user.md`) fit persistent or governed workspaces — multi-day/multi-agent work
or an explicit user request. Do not generate project-management markdown just
because a repository exists; the session itself is the artifact for ordinary
work.

## Conventions (defaults; the project wins)

- Branches: at most three hyphen-separated lowercase words, no slashes, no
  type prefixes; `main` is the long-lived branch.
- Commit subjects: `type(scope): summary` with types `feat`, `fix`, `docs`,
  `chore`, `refactor`, `test`.
- `~/.agents` stays a configuration/skill surface: no package manifests or
  dependency trees; no system rebuilds or installs unless asked.

## Global layout & host wiring (facts)

- `skills/` — one directory per skill, `SKILL.md` with `name` +
  trigger-first `description` ≤1024 chars. Grammar: `skills/writing-skills/`;
  skeleton: `templates/skill.md`. Foundations (`*-foundation`) are retrieval
  shortcuts to proven code — the source they point at is the authority.
- `templates/` — 18 CLI-neutral format templates; `essentials/` — the
  operating baseline; `mcp/servers.json` — canonical MCP registry (per-CLI
  configs are derived copies; fix drift here, never in the mirrors);
  `references/` — contract capsules.
- Host mounts: pi reads `~/.agents/skills` natively; Claude Code
  (`~/.claude/skills`, `~/.claude/CLAUDE.md`), DSH (`~/.dsh/skills`), Codex
  (`~/.codex/skills`, `~/.codex/AGENTS.md`), OpenCode
  (`~/.config/opencode/skills`, `~/.config/opencode/AGENTS.md`), and Gemini
  CLI (`~/.gemini/GEMINI.md`) read this tree via symlinks/additive merges.
