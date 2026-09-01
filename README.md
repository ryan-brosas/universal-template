# ~/.agents: the global configuration baseline for AI coding agent CLIs

This directory is the **global baseline** for the configured agent CLIs on
this machine (pi, Claude Code, Codex/OpenCode, Gemini/Antigravity, Cursor Agent,
DSH, Veda, and subprocess agents): a skill catalog with deterministic gates,
CLI-neutral templates, reusable user prompts, policy documents, and the wiring
that makes one setup serve many CLIs.
Entry flow for unfamiliar repositories: `skills/project-bootstrap/SKILL.md`.

## Layout

| Path | Contents |
| --- | --- |
| `skills/` | the active skill catalog (practice + workflow skills) |
| `foundation-pack/` | accumulated implementation foundations (`*-foundation`), separate from the active skill catalog; project source and `reference/` outrank them |
| `templates/` | CLI-neutral format templates; the filesystem is the inventory and `scripts/catalog-quality.py` checks structural invariants |
| `prompts/` | plain-Markdown reusable user prompts; `scripts/install-prompts.py` derives native CLI mounts |
| `essentials/` | cold rationale and decision references, indexed in `essentials/README.md`; read the smallest relevant file when a policy decision needs explanation |
| `docs/` | human-facing documentation, current objectives, and generated skill catalog |
| `extensions/style-guard.ts` | optional Pi output-style guard (audit by default; symlinked into `~/.pi/agent/extensions/`) |
| Entry skills (`project-bootstrap`, `brainstorming`, `goal-setup`, `prototype`, `leverage-capture`) | project entry, direction, durable goals, cheap learning, leverage classification |
| `mcp/` | the shared MCP registry (`servers.json`) and human-facing host-wiring docs (`catalog.md`); per-CLI configs are derived copies |
| `scripts/` | deterministic repository maintenance and CI gates |
| `AGENTS.md` | the global agent rules every host loads |
| `.github/` | the CI gate suite, PR automation (labels, release notes), Dependabot, issue forms, and community files |

## How to use

- **Normal work**: inspect current code and evidence → implement → run the
  relevant verification → finish. No lifecycle machinery required.
- **Prompt shortcuts**: use the canonical files in `prompts/`; run
  `python3 scripts/install-prompts.py` to install or reconcile native mounts,
  `--check` to audit host mounts, and `--check-repo` to validate canonical prompts.
- **Frontend prior art**: capture a live website with `web-reference` into
  `reference/web/<site>/` and consume it with the same ADOPT / ADAPT / OMIT
  loop as repository references; validate bundles with
  `scripts/web-reference-manifest.py`.
- **Standard baseline**: "create this repo with our standard setup",
  "production-ready", or "OSS-ready" composes `project-bootstrap` →
  `github-repo-setup` (profile from its `references/setup-matrix.md`) →
  `github-actions-engineering` → `git-workflow-and-versioning` when versioned.
  "Start a new project" stays bootstrap-only.
- **Skill catalog maintenance** (this repo only): `python3 scripts/skill-catalog.py
  search "github release"` (or `list`, `show`, `stats`, `generate`) for explicit
  catalog queries or catalog edits; not for ordinary project work elsewhere.
- **Enter a project**: `skills/project-bootstrap/SKILL.md`: read-only
  onboarding by default; governance and greenfield modes when asked.
- **Complex execution**: `skills/fabric-native-execution/SKILL.md` when multi-agent
  isolation is already required.
- **GitHub operations**: repository setup and remote audit
  (`skills/github-repo-setup`, `python3 scripts/github-audit.py`); CI and
  workflows (`skills/github-actions-engineering`); the PR lifecycle
  (`skills/push-pr`); releases and versioning
  (`skills/git-workflow-and-versioning`). Releases are `vX.Y.Z` tags published
  with generated, label-categorized notes (`.github/release.yml`).
- **MCP**: the canonical registry is `mcp/servers.json`; wire servers into
  whichever CLIs are configured, one requested server at a time (merging into
  each CLI's own config rather than overwriting it).
- **Retrieval**: inspect current project source first; use project references,
  foundations, skills, and MCPs when they materially help. Cold capability maps:
  `skills/evidence-router/SKILL.md`, `skills/execution-router/SKILL.md`. Skill
  authoring: `skills/writing-skills/SKILL.md` + `templates/skill.md`.
- **Catalog gate (this repo only)**: run the suite in `CONTRIBUTING.md`
  (repository-specific verification for this catalog, not a universal
  requirement). CI runs the same suite as the `quality / required` check via
  `.github/workflows/pr-quality.yml`.
- **Runtime probe + model resolution**: `python3 scripts/runtime-capabilities.py`
  reports the installed toolchain; `python3 scripts/resolve-model.py --role
  <role> --json` resolves a role to concrete backend/model candidates from
  live discovery. Diagnostics only; not a per-task step.
- **Prose style (layered, opt-in)**: important generated prose gets
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

| Policy                                                                                   | Canonical owner                                                            |
| ---------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| Global agent defaults (user-wide constitution)                                           | `AGENTS.md`                                                                |
| Reusable user prompt shortcuts                                                          | `prompts/` + `scripts/install-prompts.py` + `scripts/render-prompt.py`      |
| Evidence capability map (cold reference)                                                 | `skills/evidence-router`                                                   |
| Execution escalation reference (cold)                                                    | `skills/execution-router`                                                  |
| Backend/model resolution (mechanical, runtime-discovered; internal)                      | `skills/model-resolution` + `scripts/resolve-model.py`                     |
| GitHub Actions CI/CD (workflow files, check contract, release workflow)                  | `skills/github-actions-engineering`                                        |
| GitHub repository remote state (metadata, labels, rulesets, security, releases settings) | `skills/github-repo-setup` + `scripts/github-audit.py`                     |
| PR title metadata and release-note categories                                            | `scripts/pr-metadata.py` + `.github/release.yml`                           |
| PR lifecycle (push, PR, reviews, auto-merge on request)                                  | `skills/push-pr`                                                           |
| Git release strategy and versioning                                                      | `skills/git-workflow-and-versioning`                                       |
| Prior-art/reference-driven implementation                                                | `skills/reference-driven-development`                                      |
| Skill catalog maintenance (generated docs, explicit catalog queries)                     | `scripts/skill-catalog.py` + `docs/skill-catalog.md`                       |
| Catalog verification (this repository only)                                              | `CONTRIBUTING.md` + `.github/workflows/pr-quality.yml`                     |
| Reference rules (repository + web)                                                       | `skills/reference-driven-development/references/contract.md`                                         |
| Fabric execution, Schema modes, agents/Veda escalation (pi host)                         | `skills/fabric-native-execution` + project/`~/.pi/` config                 |
| Natural-language prose style (STE-inspired)                                              | `skills/house-writing-style` + `scripts/style-lint.py`                     |
| Veda escalation specifics                                                                | `skills/veda-lane`                                                         |
| Operating principles / small-model heuristics                                            | `essentials/operating-philosophy.md` / `essentials/guiding-small-model.md` |
| MCP registry and wiring                                                                  | `mcp/servers.json` + `mcp/catalog.md`                                      |
| Runtime toolchain facts                                                                  | `scripts/runtime-capabilities.py` (probed, never frozen into docs)         |

## Source of truth

This tree is the single global source of truth, git-backed at
github.com/ryan-brosas/universal-template (public). Updates are checked in
here directly; releases are cut as `vX.Y.Z` tags.

## Host mounts (how configured CLIs read this)

Existing instruction and skill mounts:

| Host        | Mount                                                                  | Points at                                         |
| ----------- | ---------------------------------------------------------------------- | ------------------------------------------------- |
| pi          | native discovery                                                       | `~/.agents/skills` (no `.pi/agent/skills` needed) |
| Claude Code | `~/.claude/skills`, `~/.claude/CLAUDE.md` → symlinks                   | `~/.agents/skills`, `~/.agents/AGENTS.md`         |
| Codex       | `~/.codex/skills`, `~/.codex/AGENTS.md` → symlinks                     | `~/.agents/*`                                     |
| OpenCode    | `~/.config/opencode/skills`, `~/.config/opencode/AGENTS.md` → symlinks | `~/.agents/*`                                     |
| Gemini CLI  | native skills discovery; `~/.gemini/GEMINI.md` → symlink               | `~/.agents/skills`, `~/.agents/AGENTS.md`         |
| DSH         | no verified global `~/.dsh/skills` mount on this host                 | use its profile configuration                     |
| Cursor Agent | no shared instruction mount is managed here                            | prompt commands are mounted below                 |
| Veda        | runner-specific personas and skills                                    | no native user-prompt directory                   |

Prompt shortcuts are canonical in `prompts/*.md` and use plain Markdown with
`$ARGUMENTS`. Available names are `/repo-audit`, `/plan-work`,
`/implement-work`, `/review-work`, `/verify-work`, and `/cleanup-code`.
Install or reconcile the native surfaces with:

```bash
python3 scripts/install-prompts.py
```

| Host                 | Native prompt surface                                      | Invocation                     |
| -------------------- | ---------------------------------------------------------- | ------------------------------ |
| pi                   | `~/.pi/agent/prompts/*.md` → symlinks                     | `/repo-audit`                   |
| Claude Code          | `~/.claude/commands/*.md` → symlinks                      | `/repo-audit`                   |
| Codex                | `~/.codex/prompts/*.md` → symlinks                        | `/prompts:repo-audit`           |
| OpenCode             | `~/.config/opencode/commands/*.md` → symlinks             | `/repo-audit`                   |
| Cursor Agent         | `~/.cursor/commands/*.md` → symlinks                      | `/repo-audit`                   |
| Gemini CLI           | `~/.gemini/commands/*.toml` → generated adapters          | `/repo-audit`                   |
| Antigravity (`agy`)  | `~/.gemini/config/global_workflows/*.md` → symlinks       | `/repo-audit`                   |
| DSH                  | no native global prompt directory verified                 | `render-prompt.py` fallback     |
| Veda                 | no native user prompt directory                            | `render-prompt.py` fallback     |

Markdown hosts share the same source file. Gemini's TOML adapter is the only
format translation; unmanaged host files are never overwritten or removed. Run
`python3 scripts/install-prompts.py --check` after installation to find missing,
stale, conflicting, or obsolete mounts. Install mode removes only obsolete
entries identified as this installer's symlinks or generated adapters.

For DSH or Veda, render the same prompt explicitly:

```bash
dsh --profile headless "$(python3 scripts/render-prompt.py repo-audit 'scope or task')"
veda "$(python3 scripts/render-prompt.py repo-audit 'scope or task')"
```

MCP registry (`mcp/servers.json`, 6 servers: codebase-memory, context7, deepwiki,
exa, openviking, mcp-steroid) is merged into: `~/.pi/agent/mcp.json`, `~/.claude.json`,
`~/.codex/config.toml` (stdio only), `~/.config/opencode/opencode.json`.
Registry commands are PATH-resolved (mise shims / local bin); machine-local
values ride in env (e.g. `CBM_CACHE_DIR`) or in the local daemon URL, never
as frozen absolute paths.
Backups live next to each host config as `*.bak-<timestamp>`.

To reproduce this setup on a fresh machine after cloning this repo to `~/.agents`,
create the instruction/skill symlinks above and run
`python3 scripts/install-prompts.py`; it skips hosts whose executable is not on
PATH and never overwrites existing unmanaged prompt files. Then merge `mcp/servers.json`
blocks into each host config (additive only, never overwrite unrequested
servers).
