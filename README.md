# ~/.agents — the global settings area for every CLI

This directory is the **global baseline** read by all agent CLIs on this
machine (pi, Claude Code, Codex/OpenCode, opencode, agy/veda, subprocess
agents). It is the absorbed, living copy of the **pi-template** repository
(`~/.agents (absorbed from the retired pi-template repo)`; contract: `references/init-contract.md`)
— the workflow we set up there, made global.

## Layout

| Path | Contents |
|---|---|
| `skills/` | the full skill catalog (foundations + practice skills + pack routers) |
| `templates/` | 18 CLI-neutral format templates (adr, agents, design, foundation-capsule, foundation-skill, github-pr-ci, issue, prd, project, proposal, pull-request, readme, roadmap, skill, state, tasks, tech-stack, user) |
| `essentials/` | the operating baseline (objectives, operating-philosophy, stack-your-leverage, steer-outcomes-not-behavior, guiding-small-model, enforce-code-quality-mechanically, how-to-build-good-tests) |
| `skills/workflow-lifecycle/` | the worldwide workflows (init, learn, audit, verify, gc) as one skill |
| `mcp/servers.json` | the **canonical** MCP registry — per-CLI configs are derived copies |
| `references/` | distilled contract capsules (init, mcp-catalog, templates-inventory) |
| `AGENTS.md` | the distilled pi-template agent rules, globalized |
| `.github/workflows/pr-quality.yml` | catalog quality CI (skill-validator + diff check + PR body contract) |

## How to use

- **Init a project**: run the `workflow-lifecycle` skill's init command (`skills/workflow-lifecycle/SKILL.md`,
  details in `skills/workflow-lifecycle/references/init.md`) — use the templates from `templates/`.
- **MCP**: the canonical registry is `mcp/servers.json`; wire servers into
  whichever CLIs are configured, one requested server at a time (merging into
  each CLI's own config rather than overwriting it).
- **Learn**: the five-source context plane (codebase-memory, openviking,
  context7, exa, deepwiki) feeds every workflow; skill authoring follows one
  uniform grammar — `skills/writing-skills/SKILL.md` + `templates/skill.md`.
- **Daily loop**: `skills/workflow-lifecycle/SKILL.md` — init once, AGENTS.md
  is the spine, slice-by-slice with context before code, documents after
  implementation, the learn command closes the loop.
- **Catalog gate**: `SKILLS_ROOT="$PWD/skills" python3 scripts/skill-validator.py`
  (exit 0 iff no P0). CI runs the same command via `.github/workflows/pr-quality.yml`.

## Source of truth

The pi-template repo was the historical source; it is retired and fully absorbed
here. This `~/.agents` tree IS the single global source of truth — git-backed at
github.com/ryan-brosas/universal-template (private). Updates are checked in here
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

MCP registry (`mcp/servers.json`, 5 servers: codebase-memory, context7, deepwiki,
exa, openviking) is merged into: `~/.pi/agent/mcp.json`, `~/.claude.json`,
`~/.codex/config.toml` (stdio only), `~/.config/opencode/opencode.json`.
Backups live next to each host config as `*.bak-<timestamp>`.

To reproduce mounts on a fresh machine after cloning this repo to `~/.agents`:
create the symlinks above, then merge `mcp/servers.json` blocks into each host
config (additive only, never overwrite unrequested servers).
