# universal-template

Shared rules and reusable playbooks for coding agents. Keep instructions small,
load procedures when needed, and answer code questions from current source—not
stored repository summaries.

## Get started

Clone into an unused directory:

```sh
git clone https://github.com/ryan-brosas/universal-template.git
```

Configure your agent to read [AGENTS.md](AGENTS.md) and discover skills from
`skills/`. Setup depends on your agent; cloning alone does not enable anything.
Expose only `skills/` to skill discovery, not `knowledge/`.

Choose a pack for the task. It points to the relevant playbook and references;
read only what you need. Simple tasks do not require a playbook.

| Pack | Use for |
| --- | --- |
| [Engineering](skills/engineering-pack/SKILL.md) | Code, debugging, tests and architecture |
| [Design](skills/design-pack/SKILL.md) | UI/UX, accessibility and visual design |
| [Delivery](skills/delivery-pack/SKILL.md) | Git, PRs, CI, deployments and releases |
| [Research](skills/research-pack/SKILL.md) | Source, documentation and web research |
| [Writing](skills/writing-pack/SKILL.md) | Prose, copy and documentation |
| [Agent tooling](skills/agent-tooling-pack/SKILL.md) | Pi, Fabric, providers and models |
| [Maintenance](skills/maintenance-pack/SKILL.md) | Updating this template and its playbooks |

## How context works

Use local source, tests and development tools for the current repository.
Use Sourcebot for code across intentionally indexed repositories, GitHub to
find unknown implementations, and official docs or Context7 for library questions.
Verify behavior with tests and runtime evidence.

Keep reusable procedures here—not copies or summaries of other repositories.
See the [evidence guide](knowledge/playbooks/evidence-router/README.md) for details.

## Repository layout

- [AGENTS.md](AGENTS.md) — shared rules.
- [skills/](skills/) — task routers.
- [knowledge/playbooks/](knowledge/playbooks/) — procedures, references and helpers.
- [prompts/](prompts/) and [templates/](templates/) — optional starting points.
- [mcp/](mcp/catalog.md) — optional tool registry and profiles; configure connections
  in your agent. The `minimal` profile enables nothing.
- [config/model-profiles.yaml](config/model-profiles.yaml) — optional task requirements.

No installer, specific model or MCP server is required.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md) and
[LICENSING.md](LICENSING.md).
