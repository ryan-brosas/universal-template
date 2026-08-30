---
purpose: Source template for the AGENTS.md file /init generates.
updated: 2026-08-16
---

# AGENTS.md template

Render a short operational file. Each instruction must describe a verified
repository fact, a measurable outcome, an irreversible-action boundary, or a
specific trap that automation cannot express.

## How to render

1. Discover the repository's real commands and run them before naming them.
2. Select one canonical completion command. If none exists, list the verified
   command set and mark the missing aggregate check.
3. Record repository-specific invariants with file or command evidence.
4. Record generated-file ownership, cache invalidation rules, packaging traps,
   and deployment checks only when local evidence proves them.
5. Include destructive-action and secret boundaries. Keep other workflow and
   style preferences out of the rendered file unless a checker enforces them.
6. Merge verified user-authored constraints. Remove stale generated guidance
   only with user approval.
7. Preview material changes before writing.
8. Keep the rendered file short. Durable non-obvious context lives in the
   project's context file (e.g. `docs/project-context.md`) when one exists —
   link to it; never recreate global routing or tool ownership here.

Do not copy generic coding doctrine, research philosophy, prose rules, planning
rituals, or examples from another repository. Do not invent commands.

---

# Agent Rules

## Golden rule: check when done

```sh
[verified check command]
```

[State exactly what the command runs, what a green result proves, and whether a
build or restart is required.]

## Repository facts

- [What this repository ships and who uses it.]
- [Runtime, language, and package manager facts proven by manifests or config.]
- [Where the durable context record lives, if one exists.]

Evidence: [paths or command output]

Do not restate global routing, tool ownership, or model policy here — the
user's global `AGENTS.md` owns those. This file adds LOCAL information only.

## Safety boundaries

- Normal reversible edits inside the git workspace (modify tracked source,
  create files, delete obsolete tracked files the task requires) need no
  repeated permission; deleting untracked or user data does.
- Require explicit confirmation before irreversible commands. Quote the command
  and list the affected files, history, infrastructure, or data.
- Never expose, invent, or commit credentials.
- Preserve unrelated working-tree changes and scope staging by path.
- Assume nothing. Before relying on any capability, verify its live state:
  check that MCP servers and tools are actually registered and connected
  (list them; do not assume), that websearch hits are opened and sourced
  (do not assume relevance), and that a code-memory graph actually covers the
  code being cited (check index coverage; do not assume it is indexed). Do not
  assume the codebase — read the source when it matters.
- [Add a project-specific production or data boundary only when verified.]

## Repository invariants

- [A dependency, compatibility, generation, security, or packaging rule that a
  checker enforces.]
- [A stable runtime or ownership boundary with its check.]

Evidence: [validator, test, workflow, manifest, or config]

## Operational traps

- [Cache invalidation trigger and exact version key.]
- [Generated source and regeneration command.]
- [Packaging, publication, migration, or deployment behavior that differs from
  local development.]

Omit this section when no verified trap exists.

## Product map (only when non-obvious)

- `[path]`: [responsibility]

Omit when the layout is self-explanatory from the tree. Never copy global
philosophy into a project file — point to the global essentials instead.

## Conventions

Include only conventions with a mechanical check or an external protocol, such
as a commit-message gate, exact budget assertion, or required PR check.

- Branch names: at most three hyphen-separated lowercase words, no slashes,
  no type prefixes (`feat/`, `fix/`); `main`/`master` are the long-lived
  branches.
- Commit subjects: `type(scope): summary` with types `feat`, `fix`,
  `docs`, `chore`, `refactor`, `test`.
  [State the exact enforcement point — e.g. the golden check on unpushed
  commits, or CI on pull-request commits.]

Omit this section when no enforced convention exists.

## Verification evidence

A completion claim requires the exit code and inspected output from the golden
check. If CI or deployment exists, state the exact watch or live verification
command.
