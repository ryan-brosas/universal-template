# universal-template

Reusable engineering principles and procedures for capable coding agents.
The host chooses the model and provides tools; this template teaches how to work.

## Get started

Clone this repository into an unused directory. Configure your agent to read
[AGENTS.md](AGENTS.md) and discover the task routers in `skills/`.
Cloning alone does not configure your agent. Expose only `skills/` to skill
discovery, and load a playbook only when it helps the task.

## Work from evidence

1. Inspect the current project's source, Git history, tests and development tools.
2. Identify what is unknown and retrieve only the evidence needed.
3. Use Sourcebot for intentionally indexed cross-repository source. Use GitHub
   to discover implementations outside that corpus, and installed source,
   official documentation or Context7 for library questions.
4. Read decisive source and tests. The coding agent reasons about the evidence,
   compares constraints, and chooses what to adopt, adapt or omit.
5. Implement locally and verify with the project's tests, compiler, runtime and CI.

Local work stays local; a known file needs a direct read, not an external search.
Sourcebot's deployment, credentials, repository configuration and indexes live
outside this template. Add inspiration repositories only when real project needs
show repeated usefulness or strategic value—not automatically after research.

## Find a procedure

| Pack | Task |
| --- | --- |
| [Engineering](skills/engineering-pack/SKILL.md) | Implementation, debugging, testing and architecture |
| [Design](skills/design-pack/SKILL.md) | UI/UX, accessibility and visual design |
| [Delivery](skills/delivery-pack/SKILL.md) | Git, PRs, CI, deployment and releases |
| [Research](skills/research-pack/SKILL.md) | Source, documentation and web investigation |
| [Writing](skills/writing-pack/SKILL.md) | Prose and documentation |
| [Agent tooling](skills/agent-tooling-pack/SKILL.md) | Agent integrations and tool troubleshooting |
| [Maintenance](skills/maintenance-pack/SKILL.md) | Maintaining reusable instructions |

## Layout

- `AGENTS.md` — durable engineering principles.
- `skills/` — small task-oriented routers.
- `knowledge/playbooks/` — reusable ways of working.
- `mcp/` — optional capability declarations and connection guidance.
- `prompts/` — reusable task starters.
- `templates/` — reusable project and output shapes.

Keep procedures here; retrieve repository knowledge from its source.
No particular model or MCP server is required for ordinary local work.

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md) and
[LICENSING.md](LICENSING.md).
