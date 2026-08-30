# ~/.agents: the global settings area for every CLI

This directory is the **global baseline** read by all agent CLIs on this
machine (pi, Claude Code, Codex/OpenCode, opencode, agy/veda, subprocess
agents). It is the absorbed, living copy of the **pi-template** repository
(`~/.agents (absorbed from the retired pi-template repo)`; entry flow: `skills/project-bootstrap/SKILL.md`):
the workflow we set up there, made global.

## Layout

| Path | Contents |
|---|---|
| `skills/` | the full skill catalog (foundations + practice skills + workflow skills) |
| `templates/` | 18 CLI-neutral format templates (adr, agents, design, foundation-capsule, foundation-skill, github-pr-ci, issue, prd, project, proposal, pull-request, readme, roadmap, skill, state, tasks, tech-stack, user) |
| `essentials/` | cold rationale and decision references (operating-philosophy plus six one-page principles); read the smallest relevant file when a policy decision needs explanation |
| `docs/roadmap.md` | current work objectives (moved out of Essentials; reviewed at milestones) |
| `extensions/style-guard.ts` | optional Pi output-style guard (audit by default; symlinked into `~/.pi/agent/extensions/`) |
| Entry skills (`project-bootstrap`, `brainstorming`, `goal-setup`, `prototype`, `leverage-capture`) | project entry, direction, durable goals, cheap learning, leverage classification |
| `mcp/servers.json` | the **canonical** MCP capability registry (6 servers incl. mcp-steroid); per-CLI configs are derived copies |
| `references/` | distilled contract capsules (init, mcp-catalog, templates-inventory) |
| `AGENTS.md` | the distilled pi-template agent rules, globalized |
| `.github/workflows/pr-quality.yml` | catalog quality CI (the full AGENTS.md gate suite, including style lint) |

## How to use

- **Enter a project**: `skills/project-bootstrap/SKILL.md`: read-only onboarding by
  default; governance and greenfield modes when asked. Uses `templates/` selectively.
- **MCP**: the canonical registry is `mcp/servers.json`; wire servers into
  whichever CLIs are configured, one requested server at a time (merging into
  each CLI's own config rather than overwriting it).
- **Retrieval**: need-driven: one primary route, escalate on a named gap,
  stop when the named uncertainty is closed (`skills/evidence-router/SKILL.md`);
  the registry (codebase-memory, openviking, context7, exa, deepwiki) supplies
  the routes. Skill authoring follows one uniform grammar:
  `skills/writing-skills/SKILL.md` + `templates/skill.md`.
- **Long-running goals (opt-in)**: `skills/goal-setup/SKILL.md`: one durable
  execution contract for significant multi-session work. A normal task stays:
  inspect → implement → verify → finish.
- **Catalog gate (this repo only)**: run the suite listed under "Finish line"
  in `AGENTS.md` (`skill-validator`, `catalog-integrity`, `catalog-quality`,
  `repo-hygiene`, `policy-consistency`, `dead-code`, `conventional-commit`,
  `git diff --check`): repository-specific verification for this catalog, not
  a universal requirement. CI runs the same suite via
  `.github/workflows/pr-quality.yml`.
- **Runtime probe + model resolution**: `python3 scripts/runtime-capabilities.py`
  reports the installed toolchain (gh, pi, pi-fabric, veda, agy, fovea,
  steroid, devrig, codebase-memory, openviking, MCP registry state);
  `python3 scripts/resolve-model.py --role <role> --json` resolves a chosen
  role to concrete backend/model candidates from live discovery. Diagnostics
  only; not a per-task step. Runtime facts stay here and in `state/`
  (gitignored), never frozen into philosophy or tracked config.
- **Prose style (layered, opt-in)**: write plain technical English (kernel in
  `AGENTS.md`); important generated prose gets
  `python3 scripts/style-lint.py <file>`; detailed rules and the rewrite
  procedure live in `skills/house-writing-style/SKILL.md`. The optional Pi
  output guard (`extensions/style-guard.ts`) audits final assistant prose and
  never rewrites by default.
- **Reference contract**: `<project>/reference/<repo>/` is implementation
  prior art; see `references/reference-contract.md` (one reference first,
  current project's tests are the acceptance authority, licensing obligations
  when materially copying).
- **Veda-managed skills**: `veda-plan`, `veda-plan-implement`,
  `veda-plan-implement-review`, `veda-deep-plan`, and `veda-worker` are
  installed and updated by `veda skills install`; vendor-managed assets, do
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
| Universal execution invariants (session-loaded constitution) | `APPEND_SYSTEM.md` |
| Global engineering policy, routing summary, machine wiring | `AGENTS.md` |
| Evidence and tool routing (NEED + HOST) | `skills/evidence-router` |
| Execution shape (Main/child/parallel/RLM/actor, write isolation) | `skills/execution-router` |
| Backend/model resolution (mechanical, runtime-discovered; internal) | `skills/model-resolution` + `scripts/resolve-model.py` |
| GitHub Actions CI/CD (.github/workflows/**, CI contract, release/deploy workflows) | `skills/github-actions-engineering` |
| Prior-art/reference-driven implementation | `skills/reference-driven-development` |
| Reference-repository rules | `references/reference-contract.md` |
| Fabric execution, Schema modes, agents/Veda escalation | `skills/fabric-native-execution` |
| Natural-language prose style (STE-inspired) | `skills/house-writing-style` + `scripts/style-lint.py` |
| Veda escalation specifics | `skills/veda-lane` |
| Operating principles / small-model heuristics | `essentials/operating-philosophy.md` / `essentials/guiding-small-model.md` |
| MCP registry and wiring | `mcp/servers.json` + `mcp/catalog.md` |
| Runtime toolchain facts | `scripts/runtime-capabilities.py` (probed, never frozen into docs) |

## Source of truth

The pi-template repo was the historical source; it is retired and fully absorbed
here. This `~/.agents` tree IS the single global source of truth, git-backed at
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
