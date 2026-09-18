---
title: session-improvement-compiler
summary: 'Use for explicit requests to compile session experience into a reusable, discoverable method: understand the lesson, state the method, place it at its owner, and show a fresh task can use it. Reflection alone does not authorize changes; compilation does not authorize repairing the original implementation.'
kind: playbook
---

# Learn from session experience

Source retrieval recovers code knowledge. Sessions supply experience. Reflection
helps explain it; compilation turns demonstrated experience into a reusable method
another session can find and apply.

## Intent and scope

Recall answers a historical question. Reflection explains lessons without changing
anything. An explicit improvement request (including `compile-session-improvements`)
authorizes compiling a reusable method into its owner. `compile-skill` asks for the
same deliverable directly. Neither makes every observation suitable for a skill.

Compilation produces a method, not a repair. Its output is reusable judgment —
technique, decision sequence, boundary, recovery or verification — made discoverable
from the task that needs it. A defect, stale plan or unfinished implementation you
notice while compiling is a finding to report; repairing it needs its own
authorization from the current request.

A learning request does not authorize changes to other projects, external systems,
or shared machine configuration. Name a concrete scope/access blocker rather than
replacing a needed repair with global advice. Continue with authorized work.

A separately authorized repair can be adopted alongside compilation; finishing the
old feature backlog does not, unless the current request also asks for it. Verify
the compiled method against a representative future task, not the old deliverable's
passing tests.

## From experience to method

1. **Inspect the work.** Bound the session and relevant task. Use selected events,
   tool results, user corrections, changes, tests, and runtime evidence. Inspect
   successes as carefully as failures: a useful comparison, shortcut, implementation
   pattern, or recovery can matter more than another prohibition. Any available
   history service may help locate evidence; none is required. Follow summaries
   back to supporting evidence, not whole-history dumps.
2. **Understand the lesson.** Explain what happened, what seems to have caused it,
   what is demonstrated versus plausible, and the conditions and exceptions. Check
   current source before prescribing a repair. Consider counter-evidence and
   alternative explanations. Use [evidence guidance](references/evidence-contract.md)
   when attribution or scope is uncertain. Reason naturally; no mandatory ledger.
3. **Decide what should change.** Separate retrievable repository facts from judgment
   gained through using them. Ask what future work could reuse and whether retaining
   it is worth maintaining. One strong result or durable user correction can justify
   adoption; recurrence strengthens evidence but is not required. State the reusable
   method in one sentence — its trigger and the technique it supplies — before
   searching for its owner, so the deliverable stays a method rather than another
   pass over the original work. When the user names `.agents`, prompts or skills as
   the target, that method is the outcome. Existing guidance that already covers the
   lesson needs confirmation, not a cosmetic edit; a defect you found is a separate
   finding, not the compile result.
4. **Compile the method into its owner.** Reuse a fitting existing playbook or skill
   and update it; when none genuinely fits, add one small specialist and link it from
   the cold index of the existing pack that already owns that task family. A new
   visible pack needs demonstrated routing need, not a single new method. Retain the
   concrete technique, decision sequence, boundary, shortcut or verification the
   method demonstrated, not a transcript digest or generic advice. Follow
   [writing-skills](../writing-skills/README.md) for that destination and
   [leverage-capture](../leverage-capture/README.md) only to confirm the owner.
   Preserve project rationale locally, and keep private session details out of
   shared guidance.
5. **Verify the effect.** Start from a fresh representative task, let it route
   through the actual procedure entry point, and inspect whether it finds and
   applies the method. Check important exceptions. A file write or rule quotation is
   not task success. Use [representative cases](references/behavior-tests.md) to
   select relevant checks, not a fixed ritual. No new catalog generator, custom
   skill validator, scoring system, or mandatory report is needed.
6. **Close honestly.** Explain the compiled method, its owner, the evidence, and what
   future work should do differently. Distinguish **saved** (written), **adopted**
   (the correct owner/consumer now behaves differently), and **shown useful**
   (representative work demonstrates benefit). State untested explanations and
   blocked candidates. Report a repair you did not execute as a named finding with
   its evidence, not as adopted work.

Evaluation should match consequence. Material method or routing changes can justify
a bounded outcome comparison with comparable starting conditions; do not invent a
failing baseline. Existing traces may suffice for narrower additions, with their
limits stated. No change is complete merely because more instructions exist.
