# universal-template

A shared, content-first baseline for coding agents. Read what the task needs.
No installer, prompt renderer, prescribed model or mandatory workflow is required.

## Contents

- `AGENTS.md`: standing global rules; project instructions add context, not exceptions.
- `skills/`: seven small pack routers, the template's only discoverable skills.
- `knowledge/playbooks/`: specialist procedures with their references and helpers.
- `prompts/` and `templates/`: optional task prompts and reusable documents.
- `mcp/`: optional server declarations and profiles, not an active connection set.
- `config/model-profiles.yaml`: optional task needs, not model rankings.

## Use

```sh
git clone https://github.com/ryan-brosas/universal-template.git ~/.agents
```

Point your agent at the checkout. Choose a pack by the task:

| Pack | Task |
| --- | --- |
| [Engineering](skills/engineering-pack/SKILL.md) | Code, debugging, tests, architecture, security, language practices |
| [Design](skills/design-pack/SKILL.md) | UI/UX, visual prototypes, Paper/Figma, accessibility, fidelity |
| [Delivery](skills/delivery-pack/SKILL.md) | Git, PRs, CI, GitHub governance, deployment and releases |
| [Research](skills/research-pack/SKILL.md) | Source and documentation investigation, search, browser and data research |
| [Writing](skills/writing-pack/SKILL.md) | Copy, prose, documentation and content |
| [Agent tooling](skills/agent-tooling-pack/SKILL.md) | Pi, Fabric, providers, models and explicit Veda workflows |
| [Maintenance](skills/maintenance-pack/SKILL.md) | This template, authoring and missing-specialist discovery |

Read the selected router, then one matching playbook and only its needed
references. Known playbook paths can be read directly; trivial tasks do not
require a procedure. Project requirements, source, tests and runtime behavior
remain authoritative.

### Where code context comes from

The template keeps no copy of other repositories. A code question resolves from
the nearest sufficient evidence:

- the current project's source, tests, Git history and IDE/LSP, using the tools
  the host already has;
- Sourcebot indexed cross-repository search when the question spans
  repositories we intentionally index or needs an implementation we do not have
  locally (`knowledge/playbooks/cross-repo-source/README.md`);
- GitHub discovery when the implementation is unknown, followed by reading the
  actual source and tests;
- installed source, official docs or Context7 for library documentation;
- tests, compiler and runtime output for behavior that must be observed.

An index or summary is a fast map, not authority: confirm exact code before
editing or claiming absence. Sources and boundaries are mapped in
`knowledge/playbooks/evidence-router/README.md`; MCP selection lives in
`mcp/catalog.md`.

### Keep startup small

Expose only `skills/` to host discovery, never `knowledge/`. Playbooks use
`README.md` with `title`, `summary` and `kind: playbook`, not skill frontmatter.
Their helpers and relative references resolve from that playbook's directory.
Do not create specialist `SKILL.md` aliases or copied inventories.

Hosts differ: verify their real discovery and outgoing context. Some list every
skill, some preload bodies, and extensions can inject additional resources.
Private and package-owned skills are separate from the seven template routers;
use supported host filters where needed, without moving installed package files
or removing essential runtime instructions.

Old leaf commands such as `/skill:ship-pr` are no longer registered by the
template. On hosts supporting skill commands, use `/skill:delivery-pack ship-pr`,
or read `knowledge/playbooks/ship-pr/README.md` directly. Slash commands are
optional; no host-specific syntax is required to use the content.

### Optional tools

`mcp/servers.json` is a registry. The `minimal` profile activates nothing. Connect
only needed tools through the host's configuration; see `mcp/catalog.md`.

## Maintenance

Keep reusable procedures and evidence, not session output, completed plans,
historical audit reports or host runtimes. Git preserves retired material.
Add content for demonstrated reuse, not merely because a repository was studied.

See `CONTRIBUTING.md`, `SECURITY.md` and `LICENSING.md` for review, reporting and
licensing. `scripts/pr-metadata.py` supports GitHub title/label/release automation
and `scripts/check-retired-paths.py` guards the retired context systems; neither
is required to use the template. Changes here can immediately affect
hosts linked to this checkout.
