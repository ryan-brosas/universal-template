# ~/.agents: the global configuration baseline for AI coding agent CLIs

This directory is the **global baseline** read by every agent CLI on this
machine (pi, Claude Code, Codex/OpenCode, opencode, agy/veda, subprocess
agents): a skill catalog with deterministic gates, CLI-neutral templates,
policy documents, and the wiring that makes one setup serve many CLIs.
Entry flow for unfamiliar repositories: `skills/project-bootstrap/SKILL.md`.

## Layout

| Path | Contents |
|---|---|
| `skills/` | the full skill catalog (foundations + practice skills + workflow skills) |
| `templates/` | 15 CLI-neutral format templates (plus `source.yml`, the inspo ledger); canonical list in `references/templates-inventory.md` |
| `essentials/` | cold rationale and decision references, indexed in `essentials/README.md`; read the smallest relevant file when a policy decision needs explanation |
| `docs/roadmap.md` | current work objectives (reviewed at milestones) |
| `extensions/style-guard.ts` | optional Pi output-style guard (audit by default; symlinked into `~/.pi/agent/extensions/`) |
| Entry skills (`project-bootstrap`, `brainstorming`, `goal-setup`, `prototype`, `leverage-capture`) | project entry, direction, durable goals, cheap learning, leverage classification |
| `docs/skill-catalog.md`, `docs/foundation-catalog.md` | generated human catalogs of the skill set (never hand-edit; regenerate with `scripts/skill-catalog.py`) |
| `mcp/servers.json` | the **canonical** MCP capability registry (6 servers incl. mcp-steroid); per-CLI configs are derived copies |
| `references/` | distilled contract capsules (reference contract, MCP catalog, templates inventory) |
| `AGENTS.md` | the global agent rules every host loads |
| `.github/` | the CI gate suite, PR automation (labels, release notes), Dependabot, issue forms, and community files |

## How to use

- **Normal work**: inspect current code and evidence → implement → run the
  relevant verification → finish. No lifecycle machinery required.
- **Frontend prior art**: capture a live website with `web-reference` into
  `reference/web/<site>/` and consume it with the same ADOPT / ADAPT / OMIT
  loop as repository references; validate bundles with
  `scripts/web-reference-manifest.py`.
- **Standard baseline**: "create this repo with our standard setup",
  "production-ready", or "OSS-ready" composes `project-bootstrap` →
  `github-repo-setup` (profile from its `references/setup-matrix.md`) →
  `github-actions-engineering` → `git-workflow-and-versioning` when versioned.
  "Start a new project" stays bootstrap-only.
- **Skill catalog navigation**: `python3 scripts/skill-catalog.py search
  "github release"` (or `list`, `show`, `stats`) returns scored candidates with
  class and visibility without loading the catalog.
- **Enter a project**: `skills/project-bootstrap/SKILL.md`: read-only
  onboarding by default; governance and greenfield modes when asked.
- **Unclear direction**: `skills/brainstorming/SKILL.md`. **Durable major
  goal**: `skills/goal-setup/SKILL.md`. **Prior art**:
  `skills/reference-driven-development/SKILL.md`. **Complex execution**:
  `skills/execution-router/SKILL.md`.
- **GitHub operations**: repository setup and remote audit
  (`skills/github-repo-setup`, `python3 scripts/github-audit.py`); CI and
  workflows (`skills/github-actions-engineering`); the PR lifecycle
  (`skills/push-pr`); releases and versioning
  (`skills/git-workflow-and-versioning`). Releases are `vX.Y.Z` tags published
  with generated, label-categorized notes (`.github/release.yml`).
- **MCP**: the canonical registry is `mcp/servers.json`; wire servers into
  whichever CLIs are configured, one requested server at a time (merging into
  each CLI's own config rather than overwriting it).
- **Retrieval**: need-driven: one primary route, escalate on a named gap,
  stop when the named uncertainty is closed (`skills/evidence-router/SKILL.md`);
  the registry (codebase-memory, openviking, context7, exa, deepwiki) supplies
  the routes. Skill authoring follows one uniform grammar:
  `skills/writing-skills/SKILL.md` + `templates/skill.md`.
- **Catalog gate (this repo only)**: run the suite listed under "Finish line"
  in `AGENTS.md`: repository-specific verification for this catalog, not a
  universal requirement. CI runs the same suite as the `quality / required`
  check via `.github/workflows/pr-quality.yml`.
- **Runtime probe + model resolution**: `python3 scripts/runtime-capabilities.py`
  reports the installed toolchain; `python3 scripts/resolve-model.py --role
  <role> --json` resolves a role to concrete backend/model candidates from
  live discovery. Diagnostics only; not a per-task step.
- **Prose style (layered, opt-in)**: write plain technical English (kernel in
  `AGENTS.md`); important generated prose gets
  `python3 scripts/style-lint.py <file>`; detailed rules and the rewrite
  procedure live in `skills/house-writing-style/SKILL.md`. The optional Pi
  output guard (`extensions/style-guard.ts`) audits final assistant prose and
  never rewrites by default.
- **Veda-managed skills**: `veda-plan`, `veda-plan-implement`,
  `veda-plan-implement-review`, `veda-deep-plan`, and `veda-worker` are
  installed and updated by `veda skills install`; vendor-managed assets, do
  not hand-edit; refresh via Veda. `veda-lane` is maintained in this repo.

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
| GitHub Actions CI/CD (workflow files, check contract, release workflow) | `skills/github-actions-engineering` |
| GitHub repository remote state (metadata, labels, rulesets, security, releases settings) | `skills/github-repo-setup` + `scripts/github-audit.py` |
| PR title metadata and release-note categories | `scripts/pr-metadata.py` + `.github/release.yml` |
| PR lifecycle (push, PR, reviews, auto-merge on request) | `skills/push-pr` |
| Git release strategy and versioning | `skills/git-workflow-and-versioning` |
| Prior-art/reference-driven implementation | `skills/reference-driven-development` |
| Reference rules (repository + web) | `references/reference-contract.md` |
| Fabric execution, Schema modes, agents/Veda escalation | `skills/fabric-native-execution` |
| Natural-language prose style (STE-inspired) | `skills/house-writing-style` + `scripts/style-lint.py` |
| Veda escalation specifics | `skills/veda-lane` |
| Operating principles / small-model heuristics | `essentials/operating-philosophy.md` / `essentials/guiding-small-model.md` |
| MCP registry and wiring | `mcp/servers.json` + `mcp/catalog.md` |
| Runtime toolchain facts | `scripts/runtime-capabilities.py` (probed, never frozen into docs) |

## Source of truth

This tree is the single global source of truth, git-backed at
github.com/ryan-brosas/universal-template (public). Updates are checked in
here directly; releases are cut as `vX.Y.Z` tags.

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
