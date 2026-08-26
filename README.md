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
| `templates/` | 15 CLI-neutral format templates (adr, agents, design, foundation-capsule, foundation-skill, issue, prd, project, proposal, roadmap, skill, state, tasks, tech-stack, user) |
| `essentials/` | the operating baseline (objectives, operating-philosophy, stack-your-leverage, steer-outcomes-not-behavior, guiding-small-model, enforce-code-quality-mechanically, how-to-build-good-tests) |
| `prompts/` | the worldwide workflows (init, learn, audit, verify, gc) — host-neutral markdown |
| `mcp/servers.json` | the **canonical** MCP registry — per-CLI configs are derived copies |
| `references/` | distilled contract capsules (init, mcp-catalog, templates-inventory) |
| `AGENTS.md` | the distilled pi-template agent rules, globalized |

## How to use

- **Init a project**: follow the `/init` workflow in `prompts/init.md` — use the
  templates from `templates/`.
- **MCP**: the canonical registry is `mcp/servers.json`; wire servers into
  whichever CLIs are configured, one requested server at a time (merging into
  each CLI's own config rather than overwriting it).
- **Learn**: the five-source context plane (codebase-memory, openviking,
  context7, exa, deepwiki) feeds every workflow; skill authoring follows one
  uniform grammar — `skills/writing-skills/SKILL.md` + `templates/skill.md`.
- **Daily loop**: `skills/workflow-lifecycle/SKILL.md` — init once, AGENTS.md
  is the spine, slice-by-slice with context before code, documents after
  implementation, `/learn` closes the loop.

## Source of truth

The pi-template repo at `~/.agents (absorbed from the retired pi-template repo)` is the historical
source; this directory is the living global copy of its workflow, templates,
essentials and skill catalog. Re-absorption is manual and on-demand — review
changed repo files, then copy the durable assets into `~/.agents` (templates,
essentials, improved workflows) while discarding the repo's own `scripts/` layer
unless a CLI literally needs it.
