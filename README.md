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
3. Inspect the host's skill discovery behavior before exposing `skills/`. Prefer
   native resource filtering when it can load only the tracked **hot** set
   (visible, locally owned `invocation: entry` leaves). Otherwise use a host-owned
   filtered symlink view. Do not expose the unified root unfiltered on eager or
   unverified hosts; hiding descriptions need not prevent body scanning.
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
foundation tree. Native filters can avoid maintaining another symlink inventory:
Pi 0.85.1 was verified with an exclusion for the canonical skill root and exact
hot-file inclusions. This avoids loading cold bodies, though directory discovery
still occurs. See `docs/template-effectiveness.md` for the tested boundary.

Where native filtering is unavailable, expose a host-owned hot symlink view and
disable competing automatic discovery where supported. Derive exposure from
current frontmatter, preserving intentional host extras and unmanaged files.
This is setup work, not a step before each project task. Optional maintainer
commands can inspect the exact publication set:

```sh
python3 scripts/skill-catalog.py list --surface hot --tracked-only --json
python3 scripts/skill-catalog.py context --json
```

Hidden operational skills and foundations remain cold and searchable with native
file tools. The visible `skill-catalog` entry explains where to look when useful
expertise is missing; no catalog command is required. For a foundation, inspect
its topic map and reference filenames/headings to select likely capsules and
their own source pins. Use the index only when discovery remains ambiguous. See
`docs/foundation-skill-v1.md` for earlier host measurements and limitations.

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

Static global context is `AGENTS.md` plus hot skill names and descriptions.
Selected skill bodies and references, project instructions, active tool schemas,
and conversation state are task context and are not counted as always loaded.
Project source, tests, and runtime behavior establish current software truth.
Session events preserve historical work evidence; recall and reflection are
rebuildable projections.

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

`mcp/servers.json` is a registry, not a default connection set. The `minimal`
profile activates nothing; select one single-purpose profile or server through
`mcp/configure.py`. Code graph and IDE semantics use separate profiles. See
`mcp/catalog.md` for verified host shapes, package pins,
and secret handling.

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
- Foundation migration evidence: `docs/foundation-skill-v1.md`
- Context definitions, budgets, host probes, and MCP costs: `docs/context-surfaces.md`
- Template simplification and current host/task evidence: `docs/template-effectiveness.md`
- Licensing status and blockers: `docs/licensing.md`
- Current objectives: `docs/roadmap.md`
- MCP registry and host wiring: `mcp/catalog.md`
- Security policy: `SECURITY.md`

> [!WARNING]
>
> This repository is active global configuration. Changes to linked instructions,
> skills, or prompts can affect every configured host immediately.
