---
name: prototype
description: "Use when the user wants to prototype, sanity-check a data model or state machine, mock up a UI, explore design options, or says 'prototype this', 'spike this', 'let me play with it', 'try a few designs'."
---


# Prototype

A prototype is **throwaway code that answers a question**. The question decides the shape.

## Core Principle

The question being answered decides the shape of the prototype. It is throwaway from day
one and clearly marked as such; one command to run; no persistence by default; skip the
polish; surface the state after every action or variant switch; and delete or absorb it
when done. The _answer_ is the only thing worth keeping.

## When to Use / NOT

- **Use when:** the user wants to prototype, sanity-check a data model or state machine,
  mock up a UI, explore design options, or says "prototype this", "let me play with it",
  "try a few designs".
- **NOT when:** the work is production code with real requirements — a prototype is
  throwaway by definition: no production-grade verification, no error handling beyond
  what makes it runnable, no abstractions. Use only enough validation to answer the
  prototype's question — a parser/state-machine prototype may warrant one small test;
  a UI prototype needs rendered evidence; a network prototype may need one live
  request. Verification follows the learning question.

## Workflow

1. Pick a branch: identify which question is being answered — logic/state model →
   `LOGIC.md`; look/feel → `UI.md`. If genuinely ambiguous and the user isn't reachable,
   default to the branch matching the surrounding code and state the assumption.
2. Build per the branch doc under the shared rules below.
3. Let the user play with it until the question is answered.
4. When done: capture the answer somewhere durable, then delete the prototype or fold
   the validated decision into the real code.

## Pick a branch

Identify which question is being answered — from the user's prompt, the surrounding code, or by asking if the user is around:

- **"Does this logic / state model feel right?"** → [LOGIC.md](LOGIC.md). Build a tiny interactive terminal app that pushes the state machine through cases that are hard to reason about on paper.
- **"What should this look like?"** → [UI.md](UI.md). Generate several radically different UI variations on a single route, switchable via a URL search param and a floating bottom bar.

The two branches produce very different artifacts — getting this wrong wastes the whole prototype. If the question is genuinely ambiguous and the user isn't reachable, default to whichever branch better matches the surrounding code (a backend module → logic; a page or component → UI) and state the assumption at the top of the prototype.

## Rules that apply to both

1. **Throwaway from day one, and clearly marked as such.** Locate the prototype code close to where it will actually be used (next to the module or page it's prototyping for) so context is obvious — but name it so a casual reader can see it's a prototype, not production. For throwaway UI routes, obey whatever routing convention the project already uses; don't invent a new top-level structure.
2. **One command to run.** Whatever the project's existing task runner supports — package script, Python entrypoint, or local dev command. The user must be able to start it without thinking.
3. **No persistence by default.** State lives in memory. Persistence is the thing the prototype is _checking_, not something it should depend on. If the question explicitly involves a database, hit a scratch DB or a local file with a clear "PROTOTYPE — wipe me" name.
4. **Skip the polish.** No production-grade verification, no error handling beyond what makes the prototype _runnable_, no abstractions — but do include the minimal check that answers the question (one small test for tricky logic, one rendered screenshot for UI, one live request for a network spike).
5. **Surface the state.** After every action (logic) or on every variant switch (UI), print or render the full relevant state so the user can see what changed.
6. **Delete or absorb when done.** When the prototype has answered its question, either delete it or fold the validated decision into the real code — don't leave it rotting in the repo.

## When done

The _answer_ is the only thing worth keeping from a prototype. Capture it somewhere durable (commit message, ADR, issue, or a `NOTES.md` next to the prototype) along with the question it was answering. If the user is around, that capture is a quick conversation; if not, leave the placeholder so they (or you, on the next pass) can fill in the verdict before deleting the prototype.

## Red Flags

- Picking the wrong branch — the two branches produce very different artifacts; getting
  this wrong wastes the whole prototype.
- Naming the prototype so a casual reader mistakes it for production.
- Adding production-grade verification, error handling, or abstractions the prototype
  doesn't need to answer its question.
- Inventing a new top-level routing structure for throwaway UI routes.
- Leaving the prototype rotting in the repo after its question is answered.

## End state

Report the prototype's outcome explicitly:

```
Question tested:
Result:
What was learned:
What should carry into production:
What should be discarded:
Next step:
```

Do not silently treat prototype code as production implementation — it is deleted or explicitly absorbed, and the report says which.

## Verification

- The prototype starts with one command using the project's existing task runner,
  without thinking.
- After every action (logic) or on every variant switch (UI), the full relevant state is
  printed or rendered, so the user can see what changed.
- The end-state report exists (question, result, carry-forward, discard) before the
  prototype is deleted or absorbed.

## References

- [LOGIC.md](LOGIC.md) — logic/state-machine branch: a tiny interactive terminal app that pushes the state machine through cases hard to reason about on paper.
- [UI.md](UI.md) — UI branch: several radically different UI variations on a single route, switchable via a URL search param and a floating bottom bar.
