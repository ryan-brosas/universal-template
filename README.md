<div align="center">

# universal-template

**One global baseline for AI coding agent CLIs**

Clone once to `~/.agents` to share engineering policy, skills, prompts,
templates, references, and MCP declarations across supported hosts.

[![checks](https://img.shields.io/github/actions/workflow/status/ryan-brosas/universal-template/pr-quality.yml?branch=main&style=for-the-badge&label=checks)](https://github.com/ryan-brosas/universal-template/actions/workflows/pr-quality.yml) [![release](https://img.shields.io/github/v/release/ryan-brosas/universal-template?style=for-the-badge)](https://github.com/ryan-brosas/universal-template/releases/latest)

</div>

## Run

No implementation language or installer is required. Point a capable coding
agent at this checkout and ask it to connect the baseline to the hosts available
on the current machine. The canonical content is plain Markdown and JSON:

- `AGENTS.md`: global engineering instructions
- `skills/`: operational capabilities plus manual, hidden `kind: foundation` evidence leaves
- `prompts/`: reusable workflows
- `templates/`: project and contribution templates
- `mcp/servers.json`: portable MCP declarations

Project source and local instructions remain authoritative over this baseline.

## Model-native setup

```sh
git clone https://github.com/ryan-brosas/universal-template.git ~/.agents
cd ~/.agents
```

Then have the active coding agent perform this bounded setup:

1. Detect available hosts through their native commands and current runtime
   inventory. Do not assume that an installed executable is configured.
2. Inspect each detected host's current instruction, skill, and prompt surfaces.
   Prefer current host documentation or runtime help over remembered paths.
3. Inspect the host's skill discovery behavior before linking `skills/`. A host
   that eagerly scans the tree or whose hidden-field behavior is unverified must
   receive a host-owned filtered symlink view containing only operational leaves
   (frontmatter without `kind: foundation`), never the unified root. Only a host
   proven to discover lazily without scanning the full tree may use the root.
4. Generate a host adapter only when the host requires a different format. The
   adapter must name its canonical source under `prompts/` and remain derived.
5. Preserve every unmanaged file. Replace or remove only links and adapters
   whose ownership by this checkout is mechanically provable.
6. Read back links or generated files, compare adapters with their source, and
   report conflicts, unsupported hosts, and uncertain behavior.

This is the ordinary setup path. It uses the agent's native filesystem and host
capabilities, not Python.

### Skill exposure on eager hosts

`skills/` is the one canonical source tree; do not copy it or maintain a second
foundation tree. For eager or unverified hosts, create a host-owned directory of
symlinks to operational skill directories only, configure the host to scan that
directory, and disable its automatic `~/.agents/skills` scan where supported.
Reconcile links from current frontmatter and preserve unmanaged host files.
Maintainers can inspect the exact filtered set with:

```sh
python3 scripts/skill-catalog.py list --kind skill --json
```

Foundations remain cold and explicit: use catalog search/show, open the selected
`skills/<name>-foundation/SKILL.md`, inspect its `references/index.md`, then load
one matching capsule. See `docs/foundation-skill-v1.md` for measured host
behavior and limitations.

### Optional compatibility installer

Maintainers who want the legacy reconciler may run:

```sh
python3 scripts/install-prompts.py
```

It installs prompts only; it does not expose skills. It creates relative links
for Markdown-capable hosts and generated TOML for Gemini CLI. `--check` audits
installed mounts without changing them, and
`--home <sandbox>` supports isolated testing. This helper is optional; Python
is not required to consume or maintain the canonical content.

## Why universal-template?

| Capability | What it unlocks |
| --- | --- |
| One canonical baseline | Share instructions, prompts, templates, skills, and MCP declarations across hosts. |
| Need-driven capabilities | Discover focused procedures from skill metadata and the filesystem. |
| Exact publication checks | Protect structured data, references, generated parity, paths, secrets, and safe mutation. |

## Context model

Project source, tests, and runtime behavior establish current software truth.
Session events preserve historical work evidence. Recall and reflection are
rebuildable projections. Only reviewed code, gates, skills, and rare minimal
project notes become durable promotions.

## Usage

Use host-native operational-skill discovery or search `skills/*/SKILL.md`
directly. Read frontmatter, choose the smallest relevant capability, and load
only that skill and the references it names. `kind: foundation` leaves are cold,
historical evidence: select one explicitly and load one matching capsule.
`docs/skill-catalog.md` and `docs/foundation-catalog.md` are separate optional
generated views for human browsing, not required model context.

Reusable prompts include `/repo-audit`, `/plan-work`, `/implement-work`,
`/review-work`, `/verify-work`, `/cleanup-code`, `/learn`, `/recall-session`,
`/reflect-session`, and `/compile-skill`. Host invocation syntax can differ.
`scripts/render-prompt.py` remains an optional compatibility helper for hosts
without a native prompt surface.

MCP servers are added one at a time from `mcp/servers.json`; see
`mcp/catalog.md` for verified host shapes and secret handling.

## Maintenance

The hidden `template-maintenance` skill owns semantic review of this baseline.
Required CI is intentionally narrow and objective. See `CONTRIBUTING.md` and
`docs/maintainer-tooling.md` for the exact publication contracts and optional
Python helpers.

## Documentation

- Engineering constitution: `AGENTS.md`
- Contribution and verification contract: `CONTRIBUTING.md`
- Maintainer tool ownership: `docs/maintainer-tooling.md`
- Human operational skill catalog: `docs/skill-catalog.md`
- Human foundation catalog: `docs/foundation-catalog.md`
- Foundation migration and host probes: `docs/foundation-skill-v1.md`
- Current objectives: `docs/roadmap.md`
- MCP registry and host wiring: `mcp/catalog.md`
- Security policy: `SECURITY.md`

> [!WARNING]
>
> This repository is active global configuration. Changes to linked instructions,
> skills, or prompts can affect every configured host immediately.
