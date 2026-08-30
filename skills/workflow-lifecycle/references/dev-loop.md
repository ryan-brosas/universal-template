# The governed development loop — init → AGENTS.md → implement → verify → documents

The lifecycle commands (init/learn/audit/verify/gc) are phases of ONE governed loop.
This is the loop for projects that use lifecycle governance (persistent, multi-session,
or multi-agent work). A normal task does not need it: inspect current code/evidence →
implement → run relevant verification → finish, with no lifecycle artifacts required.

## Loop overview

```
init (once)  →  AGENTS.md is the operating spine
      │
      ▼
 retrieve context (need-driven, see mcp-context) ──┐
      │                                             │
      ▼                                             │
 implement the agreed scope (reversible when possible;│
      load `coding-best-practices` for topic routing,│
      `code-discipline` for scope)                   │
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
   command, pointers to `.pi/project.md` and `.pi/tech-stack.md`. If work
   reveals a stale fact in AGENTS.md, fix it in the same pass.
2. **Scope, not fragmentation.** Take on the task the user asked for — sized
   by agreed scope and `code-discipline`, not an artificial one-change-at-a-time
   cap. Stay scoped to the problem; do not drive-by refactor unrelated areas.
3. **Context before code, need-driven.** Before writing anything, pick the one
   primary source that answers the question (direct source, codebase-memory
   graph, OpenViking mined corpora, Context7 docs, Exa web, DeepWiki) and stop
   when evidence is sufficient — escalate only on a named gap
   (`evidence-router`). Hits are pointers; verify in source before citing.
4. **Documents after implementation, not promises.** In governed workspaces,
   state/roadmap/user updates happen after gates pass; docs describe what IS.
   Exception: design docs for genuinely new architecture. Ungoverned one-off
   tasks need no artifact at all.
5. **Follow the essentials** (`~/.agents/essentials/`) and the coding practice
   router (`coding-best-practices`) for topic-specific leaves: objectives,
   operating philosophy, steer outcomes not behavior, guiding-small-model,
   stack your leverage, enforce code quality mechanically, how to build good tests.
6. **Close the loop when it pays.** If a step taught something recurring — a
   repeatable procedure, verified debugging path, or edge case that re-derivation
   would waste — distill via the learn command into a skill
   (`~/.agents/templates/skill.md`). One-off details stay in code.

## Per-phase context map

| Phase | Primary sources | Why |
|---|---|---|
| init / detect | Fovea sketch/focus + filesystem; codebase-memory optional | structure + ground truth of the repo |
| prior experience | OpenViking (decisions, failed attempts, corpora) | only when prior mining or history helps |
| library/API questions | Context7, DeepWiki | current docs, architecture pages |
| external facts | Exa | live web, changelog, advisories |
| docs-after-verify | local files + codebase-memory | keep citations file:line precise |

## Definition of done

- Canonical completion command exits 0 (from AGENTS.md)
- Docs written/updated AFTER the green run (state.md, roadmap tick — when the project keeps .pi artifacts)
- Evidence cited (file:line or command output), not asserted
- If a lesson exists → learn candidate noted or filed
