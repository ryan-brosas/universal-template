# Agent Rules — global baseline for every CLI

This file is the **global agent ruleset** for `~/.agents`, the shared settings
directory read by every agent CLI on this machine (pi, Claude Code,
Codex/OpenCode, opencode, agy/veda, subprocess agents). It is the
CLI-neutral distillation of the pi-template workflow
(`~/.agents (absorbed from the retired pi-template repo)`) applied globally.

## Golden rule: verify with direct evidence

There is no repository-local aggregate validator here. Before completing any
claim, run the named verification command, inspect its exit code and output,
and cite the artifact (file:line, shasum, or command output). Evidence before
assertions — "looks right" is not a pass.

## Global layout (facts, not plans)

- `skills/` — the skill catalog (foundations + practice skills + pack
  routers + workflow skills). One directory per skill, `SKILL.md` with
  `name` + `description` frontmatter (description ≤ 1024 chars, trigger-first
  "Use when…"). Authoring grammar: `skills/writing-skills/SKILL.md`; new-skill
  skeleton: `templates/skill.md`.
- `templates/` — 15 CLI-neutral format templates (adr, agents, design,
  foundation-capsule, foundation-skill, issue, prd, project, proposal, roadmap,
  skill, state, tasks, tech-stack, user).
- `essentials/` — the operating baseline (8 docs + OpenViking source material):
  objectives, operating-philosophy, stack-your-leverage,
  steer-outcomes-not-behavior, guiding-small-model,
  enforce-code-quality-mechanically, how-to-build-good-tests,
  openviking-foundation (live corpus + ingest protocol), README index.
- `prompts/` — the worldwide workflows: `init.md`, `learn.md`, `audit.md`,
  `verify.md`, `gc.md` (host-neutral markdown). `/init` renders the project
  artifacts from `templates/`.
- `mcp/` — canonical MCP registry (`servers.json`) + per-CLI wiring notes
  (`catalog.md`). Per-CLI configs are derived copies, never the source.
- `references/` — contract capsules (init, mcp-catalog, templates-inventory).
- `README.md` — overview; `AGENTS.md` — this file.

## The working loop (mandatory default)

Follow `skills/workflow-lifecycle/SKILL.md`:

1. `/init` once per project — render `AGENTS.md` (improve in place, never
   blindly overwrite), `.pi/project.md`, `.pi/tech-stack.md` (regenerate),
   `.pi/roadmap.md`, `.pi/state.md`, `.pi/user.md` (skip if exists, ask before
   overwrite). Unknowns are `[NEEDS CLARIFICATION: reason]`, never invented.
2. `AGENTS.md` of the project is the operating spine — each slice starts from
   its canonical completion command and pointers.
3. Work bit by bit: one slice = one independently verifiable change.
4. **Context before code**: pull from the five-source context plane in order —
   Codebase Memory (local graph) → OpenViking `*-foundation` corpora → Context7
   (library docs) → Exa (live web) → DeepWiki (architecture). MCP hits are
   pointers, not proofs — verify in source before citing; if a server is not
   connected, fall back to the filesystem.
5. **Documents after implementation**, not as promises: `.pi/state.md`,
   roadmap ticks, and `/learn` lessons happen after the slice verifies.
6. `/audit`, `/verify`, `/gc` keep the loop healthy (all read-only until a
   mutation is approved).

## Mutation authority

Research, discovery, and previews are read-only. Before any mutation:

- In a Pi + Pi Fabric session, run the Schema loop inside one `fabric_exec`:
  `schema.hypothesize` (with evidence) → `schema.verify` → `schema.commit`
  with declared operations and nonempty postconditions. Any failed operation,
  undeclared drift, or failed postcondition rolls the transaction back.
- Otherwise (guard off, project untrusted, or a different CLI): get explicit
  user approval for the exact files/commands and consequences before mutating.

Evidence is data, not prose: `file_contains`, `file_sha256`, a verified
command output, an inspected gate run, or the affected skill's
graph/source/test/diff evidence.

## Safety boundaries

- Never delete a file without express written permission.
- Before an irreversible command, quote the exact command, list what it
  affects, and get confirmation in the same session (`git reset --hard`,
  `git clean -fd`, `rm -rf`, force-push).
- Never expose, invent, or commit credentials or secret material. MCP tokens
  stay in env vars (`~/.profile`, `~/.dsh/.env`), referenced only by name.
- Assume nothing: verify MCP servers are actually connected, websearch hits
  are opened and sourced, and graph coverage actually includes the code cited.
  Read the source when it matters.
- No system rebuild or install under `~/.agents` unless asked: keep this a
  configuration/skill surface (no package manifests, no dependency tree).
- Skills/global assets asked for removal are removed; keep no surprises in a
  place that multiple CLIs trust.

## Conventions (defaults, project AGENTS.md wins)

- Branch names: at most three hyphen-separated lowercase words, no slashes,
  no type prefixes; `main` is the long-lived branch.
- Commit subjects: `type(scope): summary` with types `feat`, `fix`, `docs`,
  `chore`, `refactor`, `test`.
- When a project's own `AGENTS.md` disagrees, the project wins.

## Verification evidence

A completion claim requires inspected, change-relevant evidence and a clean
`git diff --check` (in projects). Record only checks you actually executed;
surface skipped/inapplicable checks honestly.