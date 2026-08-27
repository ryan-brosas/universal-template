# The daily development loop — init → AGENTS.md → slices → documents

The lifecycle commands (init/learn/audit/verify/gc) are phases of ONE daily loop.
This is the default way of working with any project bootstrapped by this skill.

## Loop overview

```
init (once)  →  AGENTS.md is the operating spine
      │
      ▼
 pick one small slice ──────────────────────────────┐
      │                                             │
      ▼                                             │
 retrieve context (context plane, see mcp-context)   │
      │                                             │
      ▼                                             │
 implement the slice (bit by bit, reversible;
      load `coding-best-practices` for topic routing, `code-discipline` for scope)        │
      │                                             │
      ▼                                             │
 verify (project's own gates; AGENTS.md leads with   │
 the canonical completion command)                   │
      │                                             │
      ▼                                             │
 documents AFTER implementation ──┐                  │
      · update .pi/state.md        │                 │
      · tick roadmap item          │                 │
      · learn if a lesson emerged │                 │
      └────────────────────────────┴─────────────────┘
```

## Rules

1. **AGENTS.md is the spine.** Every iteration starts from it: completion
   command, pointers to `.pi/project.md` and `.pi/tech-stack.md`. If a slice
   reveals a stale fact in AGENTS.md, fix it in the same slice.
2. **Bit by bit.** One slice = one independently verifiable change. Never batch
   unrelated edits; never leave the tree broken between slices.
3. **Context before code.** Before writing anything, pull context (order:
   codebase-memory graph → OpenViking mined corpora → Context7 library docs →
   Exa live web → DeepWiki architecture pages). Hits are pointers; verify in
   source before citing.
4. **Documents after implementation, not promises.** state/roadmap/user updates
   happen after the slice verifies; docs describe what IS. Exception: design
   docs for genuinely new architecture.
5. **Follow the essentials** (`~/.agents/essentials/`) and the coding practice
   router (`coding-best-practices`) for topic-specific leaves: objectives,
   operating philosophy, steer outcomes not behavior, guiding-small-model,
   stack your leverage, enforce code quality mechanically, how to build good tests.
6. **Close the loop.** If a step taught something reusable, distill via the
   learn command into a skill (use `~/.agents/templates/skill.md`).

## Per-phase context map

| Phase | Primary sources | Why |
|---|---|---|
| init / detect | codebase-memory (graph), filesystem | ground truth of the repo |
| slice planning | OpenViking `*-foundation` corpora | prior mined knowledge for the stack |
| library/API questions | Context7, DeepWiki | current docs, architecture pages |
| external facts | Exa | live web, changelog, advisories |
| docs-after-slice | local files + codebase-memory | keep citations file:line precise |

## Definition of done per slice

- Canonical completion command exits 0 (from AGENTS.md)
- Docs written/updated AFTER the green run (state.md, roadmap tick)
- Evidence cited (file:line or command output), not asserted
- If a lesson exists → learn candidate noted or filed
