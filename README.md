# ~/.agents — the global settings area for every CLI

This directory is the **global baseline** read by all agent CLIs on this
machine (pi, Claude Code, Codex/OpenCode, opencode, agy/veda, subprocess
agents). It is the absorbed, living copy of the **pi-template** repository
(`~/.agents (absorbed from the retired pi-template repo)`; contract: `references/init-contract.md`)
— the workflow we set up there, made global.

## Layout

| Path | Contents |
|---|---|
| `skills/` | the full skill catalog (foundations + practice skills + workflow skills) |
| `templates/` | 18 CLI-neutral format templates (adr, agents, design, foundation-capsule, foundation-skill, github-pr-ci, issue, prd, project, proposal, pull-request, readme, roadmap, skill, state, tasks, tech-stack, user) |
| `essentials/` | the operating baseline (objectives, operating-philosophy, stack-your-leverage, steer-outcomes-not-behavior, guiding-small-model, enforce-code-quality-mechanically, how-to-build-good-tests) |
| `skills/workflow-lifecycle/` | the worldwide workflows (init, learn, audit, verify, gc) as one skill |
| `mcp/servers.json` | the **canonical** MCP capability registry (6 servers incl. mcp-steroid) — per-CLI configs are derived copies |
| `references/` | distilled contract capsules (init, mcp-catalog, templates-inventory) |
| `AGENTS.md` | the distilled pi-template agent rules, globalized |
| `.github/workflows/pr-quality.yml` | catalog quality CI (skill-validator + diff check + PR body contract) |

## How to use

- **Init a project**: run the `workflow-lifecycle` skill's init command (`skills/workflow-lifecycle/SKILL.md`,
  details in `skills/workflow-lifecycle/references/init.md`) — use the templates from `templates/`.
- **MCP**: the canonical registry is `mcp/servers.json`; wire servers into
  whichever CLIs are configured, one requested server at a time (merging into
  each CLI's own config rather than overwriting it).
- **Retrieval**: need-driven — one primary route, escalate on a named gap,
  stop when evidence is sufficient (`skills/evidence-router/SKILL.md`); the
  registry (codebase-memory, openviking, context7, exa, deepwiki) supplies the
  routes. Skill authoring follows one uniform grammar —
  `skills/writing-skills/SKILL.md` + `templates/skill.md`.
- **Governed loop (opt-in)**: `skills/workflow-lifecycle/SKILL.md` — for
  persistent/governed workspaces: init once, AGENTS.md as the spine, scoped
  work with gates before claims, documents after implementation, learn closes
  the loop. A normal task stays: inspect → implement → verify → finish.
- **Catalog gate (this repo only)**: run the suite listed under "Finish line"
  in `AGENTS.md` (`skill-validator`, `catalog-integrity`, `catalog-quality`,
  `repo-hygiene`, `policy-consistency`, `dead-code`, `conventional-commit`,
  `git diff --check`) — repository-specific verification for this catalog, not
  a universal requirement. CI runs the same suite via
  `.github/workflows/pr-quality.yml`.
- **Runtime probe**: `python3 scripts/runtime-capabilities.py` reports the
  installed toolchain (gh, pi, pi-fabric, veda, agy, fovea, steroid, devrig,
  codebase-memory, openviking, MCP registry state). Diagnostics only — not a
  per-task step. Runtime facts stay here and in machine-local config, never
  frozen into philosophy.
- **Reference contract**: `<project>/reference/<repo>/` is implementation
  prior art — see `references/reference-contract.md` (one reference first,
  current project's tests are the acceptance authority, licensing obligations
  when materially copying).
- **Veda-managed skills**: `veda-plan`, `veda-plan-implement`,
  `veda-plan-implement-review`, `veda-deep-plan`, and `veda-worker` are
  installed and updated by `veda skills install` — vendor-managed assets, do
  not hand-edit; refresh via Veda. `veda-lane` is maintained in this repo.
  Veda itself is a CLI/runner (Fabric launches it via
  `agents.run({runner: "veda"})`), not an MCP server.
- **References, two meanings**: `references/` here holds global contract
  capsules; implementation prior art lives in a project's own
  `<project>/reference/<repo>/` checkouts. Don't mix them.

## Canonical policy owners

One rule, one owner; other documents summarize and link. Machine-readable
policy invariants live in `scripts/policy-consistency.py` (CI-enforced).

| Policy | Canonical owner |
|---|---|
| Global invariants, safety boundaries, routing summary | `AGENTS.md` |
| Evidence and tool routing (NEED + HOST) | `skills/evidence-router` |
| Normal development procedure | `skills/codebase-driven-development` |
| Reference-repository rules | `references/reference-contract.md` |
| Fabric execution, Schema modes, agents/Veda escalation | `skills/fabric-native-execution` |
| Veda escalation specifics | `skills/veda-lane` |
| Operating principles / small-model heuristics | `essentials/operating-philosophy.md` / `essentials/guiding-small-model.md` |
| MCP registry and wiring | `mcp/servers.json` + `mcp/catalog.md` |
| Runtime toolchain facts | `scripts/runtime-capabilities.py` (probed, never frozen into docs) |

## Source of truth

The pi-template repo was the historical source; it is retired and fully absorbed
here. This `~/.agents` tree IS the single global source of truth — git-backed at
github.com/ryan-brosas/universal-template (public). Updates are checked in here
directly.

## Host mounts (how every CLI reads this)

| Host | Mount | Points at |
|---|---|---|
| pi | native discovery | `~/.agents/skills` (no `.pi/agent/skills` needed) |
| Claude Code | `~/.claude/skills` → symlink | `~/.agents/skills` |
| Claude Code | `~/.claude/CLAUDE.md` → symlink | `~/.agents/AGENTS.md` |
| DSH | `~/.dsh/skills` → symlink | `~/.agents/skills` |
| Codex | `~/.codex/skills`, `~/.codex/AGENTS.md` → symlinks | `~/.agents/*` |
| OpenCode | `~/.config/opencode/skills`, `~/.config/opencode/AGENTS.md` → symlinks | `~/.agents/*` |
| Gemini CLI | `~/.gemini/GEMINI.md` → symlink | `~/.agents/AGENTS.md` |

MCP registry (`mcp/servers.json`, 6 servers: codebase-memory, context7, deepwiki,
exa, openviking, mcp-steroid) is merged into: `~/.pi/agent/mcp.json`, `~/.claude.json`,
`~/.codex/config.toml` (stdio only), `~/.config/opencode/opencode.json`.
Registry commands are PATH-resolved (mise shims / local bin); machine-local
values ride in env (e.g. `CBM_CACHE_DIR`) or in the local daemon URL, never
as frozen absolute paths.
Backups live next to each host config as `*.bak-<timestamp>`.

To reproduce mounts on a fresh machine after cloning this repo to `~/.agents`:
create the symlinks above, then merge `mcp/servers.json` blocks into each host
config (additive only, never overwrite unrequested servers).
