<div align="center">

# universal-template

**One global baseline for AI coding agent CLIs**

Clone once to `~/.agents` to share engineering policy, skills, prompts,
templates, references, and MCP declarations across supported hosts.

[![checks](https://img.shields.io/github/actions/workflow/status/ryan-brosas/universal-template/pr-quality.yml?branch=main&style=for-the-badge&label=checks)](https://github.com/ryan-brosas/universal-template/actions/workflows/pr-quality.yml) [![release](https://img.shields.io/github/v/release/ryan-brosas/universal-template?style=for-the-badge)](https://github.com/ryan-brosas/universal-template/releases/latest)

</div>

## Run

Read the relevant Markdown and apply it to the current task. No installation,
prompt renderer, host configuration, external planning model, or prescribed
workflow is required. The template supplies knowledge; the active agent chooses
its approach using the project's requirements and available tools.

The canonical content is plain Markdown and JSON:

- `AGENTS.md`: global engineering instructions
- `skills/`: operational capabilities (visible entries plus hidden manuals)
- `knowledge/foundations/`: cold, source-specific evidence, reached through
  `skills/foundation-pack/`
- `prompts/`: reusable workflows
- `templates/`: project and contribution templates
- `mcp/servers.json`: portable MCP declarations

Project source and local instructions remain authoritative over this baseline.

## Using it

```sh
git clone https://github.com/ryan-brosas/universal-template.git ~/.agents
```

Point a coding agent at the checkout and let it read what the task needs. Exposing
this content to a host is the host's own work: there is no installer, no generated
adapter, and no required setup sequence.

Two facts matter when a host discovers `skills/`:

- It is the one canonical tree. Do not copy it or maintain a second one.
- Eager hosts load every skill body they find. Prefer the host's native resource
  filter, loading only the tracked **hot** set (visible, locally owned
  `invocation: entry` leaves); otherwise expose a host-owned filtered view. Do not
  expose the unified root unfiltered on an eager or unverified host, because
  hiding a description does not prevent body loading.

See `docs/template-effectiveness.md` for the measured host boundary.

### Skill exposure on eager hosts

`skills/` is the one canonical skill tree; do not copy it or maintain a second
one. Source evidence lives outside it under `knowledge/foundations/`. Native
filters can avoid maintaining another symlink inventory:
Pi 0.85.1 was verified with an exclusion for the canonical skill root and exact
hot-file inclusions. This avoids loading cold bodies, though directory discovery
still occurs. See `docs/template-effectiveness.md` for the tested boundary.

Where native filtering is unavailable, expose a host-owned hot symlink view and
disable competing automatic discovery where supported. Derive exposure from
current frontmatter, preserving intentional host extras and unmanaged files.
This is host setup work, not a step before each project task. Inspect tracked
`skills/*/SKILL.md` frontmatter directly: select locally owned `invocation: entry`
skills without `disable-model-invocation: true`.

Hidden operational skills remain cold and searchable with native file tools. The
visible `skill-catalog` entry explains where to look when useful expertise is
missing; no catalog command is required. Source evidence is not a skill: the
visible `foundation-pack` entry routes through one category to one foundation and
one matching capsule, using that capsule's own source pin. See
`docs/foundation-skill-v1.md` for earlier host measurements and limitations.

## Why universal-template?

| Capability | What it unlocks |
| --- | --- |
| One canonical baseline | Share instructions, prompts, templates, skills, and MCP declarations across hosts. |
| Need-driven capabilities | Discover focused procedures from skill metadata and the filesystem. |
| Content-first maintenance | Review Markdown directly; use focused tests for executable helpers. |

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
only that skill and the references it names. For source-specific prior art, start
at `skills/foundation-pack/SKILL.md` and load one matching capsule. The skill tree
itself is the inventory; there are no generated catalogs.

`prompts/` holds reusable workflows: `repo-audit`, `plan-work`, `implement-work`,
`review-work`, `verify-work`, `cleanup-code`, `learn`, `recall-session`,
`reflect-session`, `compile-skill`, and `compile-session-improvements`. Read one
and apply it to the current request. Some hosts expose these as slash commands;
that syntax differs by host and is not required.

`mcp/servers.json` is a registry, not a default connection set. The `minimal`
profile activates nothing; wire only what a host actually needs, using that
host's own MCP configuration. Code graph and IDE semantics use separate profiles.
See `mcp/catalog.md` for verified host shapes, package pins, and secret handling.

## Maintenance

The hidden `template-maintenance` skill owns semantic review of this baseline.
CI tests the retained executable helpers and PR metadata. See `CONTRIBUTING.md`
for direct content review and the remaining checks.

## Documentation

- Engineering constitution: `AGENTS.md`
- Contribution and verification contract: `CONTRIBUTING.md`
- Foundation migration evidence: `docs/foundation-skill-v1.md` (historical layout)
- Context definitions, historical host probes, and MCP costs: `docs/context-surfaces.md`
- Template simplification and current host/task evidence: `docs/template-effectiveness.md`
- Licensing status and blockers: `docs/licensing.md`
- Current objectives: `docs/roadmap.md`
- MCP registry and host wiring: `mcp/catalog.md`
- Security policy: `SECURITY.md`

> [!WARNING]
>
> This repository is active global configuration. Changes to linked instructions,
> skills, or prompts can affect every configured host immediately.
