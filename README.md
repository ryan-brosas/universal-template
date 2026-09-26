# universal-template

Reusable engineering principles and procedures for capable coding agents.
The host chooses the model and provides tools; this template teaches how to work.

## Get started

Clone this repository into an unused directory. Configure your agent to read
[AGENTS.md](AGENTS.md) and discover the task routers in `skills/`.
Cloning alone does not configure your agent. Expose only `skills/` to skill
discovery. For each task, load zero, one, or several packs and playbooks: the
smallest set that covers its independent subproblems, with each selected for work
it owns.

## Work from evidence

1. Inspect the current project's source, Git history, tests and development tools.
2. Identify what is unknown and retrieve only the evidence needed.
3. Match research to the question. Read known local files directly; use live
   assets and design tools for Figma/Paper work. For broad unresolved codebase
   questions, use Sourcebot's `ask_codebase` when relevant indexed coverage can
   help, following the [source research procedure](knowledge/playbooks/cross-repo-source/README.md).
   Use GitHub for implementations outside that corpus, and installed source,
   official documentation or Context7 for library questions. Reuse valid findings;
   a new session or phase does not itself require an external call.
4. Read decisive source and tests. The coding agent reasons about the evidence,
   compares constraints, and chooses what to adopt, adapt or omit.
5. Implement locally and verify with the project's tests, compiler, runtime and
   CI. Consult code again whenever a phase exposes a new uncertainty. The
   working tree and actual patch outrank an indexed snapshot.

Sourcebot's deployment, credentials, repository configuration and indexes live
outside this template. Add inspiration
repositories only when real project needs show repeated usefulness or strategic
value—not automatically after research.

## Find procedures

| Pack | Task |
| --- | --- |
| [Engineering](skills/engineering-pack/SKILL.md) | Implementation, debugging, testing and architecture |
| [Design](skills/design-pack/SKILL.md) | UI/UX, accessibility and visual design |
| [Delivery](skills/delivery-pack/SKILL.md) | Git, PRs, CI, deployment and releases |
| [Research](skills/research-pack/SKILL.md) | Source, documentation and web investigation |
| [Writing](skills/writing-pack/SKILL.md) | Prose and documentation |
| [Agent tooling](skills/agent-tooling-pack/SKILL.md) | Agent integrations, execution surfaces and typed judgments |
| [Maintenance](skills/maintenance-pack/SKILL.md) | Maintaining reusable instructions |

Packs compose when a task spans rows. Implementing a designed UI can load design
and engineering; shipping it can add delivery. Use the smallest sufficient set,
not a fixed one-pack choice or the whole library.

## Layout

- `AGENTS.md` — durable engineering principles.
- `skills/` — small task-oriented routers.
- `knowledge/playbooks/` — reusable ways of working.
- `mcp/` — optional capability declarations and connection guidance.
- `prompts/` — reusable task starters.
- `templates/` — reusable project and output shapes.

Keep procedures here; retrieve repository knowledge from its source. The
template remains portable across hosts: if relevant or explicitly requested
Sourcebot research is unavailable, report the limitation and continue from direct
evidence. Unrelated tasks need no Sourcebot availability check.

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md) and
[LICENSING.md](LICENSING.md).
