---
title: session-improvement-compiler
summary: 'Use for explicit requests to improve future work from session experience: understand successes and failures, choose the right owner, adopt within scope, and verify the benefit. Reflection alone does not authorize changes.'
kind: playbook
---

# Learn from session experience

Source retrieval recovers code knowledge. Sessions supply experience. Reflection
helps explain it; improvement adopts valuable lessons into the correct owner.
Skills and playbooks are only one possible destination.

## Intent and scope

Recall answers a historical question. Reflection explains lessons without changing
anything. An explicit improvement request (including `compile-session-improvements`)
authorizes in-scope adoption. `compile-session-skill` specifically asks for a reusable
method; it does not make every observation suitable for a skill.

A learning request does not authorize changes to other projects, external systems,
or shared machine configuration. Name a concrete scope/access blocker rather than
replacing a needed repair with global advice. Continue with authorized work.

## From experience to adoption

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
   adoption; recurrence strengthens evidence but is not required. Use
   [owner selection](../leverage-capture/README.md) to choose the kind of improvement
   before searching for its narrowest existing owner. Nothing permanent is valid.
4. **Adopt at that owner.** Fix code or configuration where they own the problem;
   add regression coverage when useful. Preserve project rationale locally. For a
   reusable method, retain its concrete technique, decision sequence, boundary, or
   shortcut and make it discoverable from the task that needs it. Use
   [writing-skills](../writing-skills/README.md) only for that destination. Prefer a
   fitting existing owner, not an unrelated skill. Do not create a transcript digest
   or another memory artifact. Keep private session details out of shared guidance.
5. **Verify the effect.** Test changed code, exercise changed integration, or try a
   representative task through the actual procedure/routing entry point. Check
   important exceptions. A file write or rule quotation is not task success. Use
   [representative cases](references/behavior-tests.md) to select relevant checks,
   not a fixed ritual. No new catalog generator, custom skill validator, scoring
   system, or mandatory report is needed.
6. **Close honestly.** Explain the adoption, owner, evidence, and what future work
   should do differently. Distinguish **saved** (written), **adopted** (the correct
   owner/consumer now behaves differently), and **shown useful** (representative
   work demonstrates benefit). State untested explanations and blocked candidates.
   Do not lose an unfinished qualified repair because an easier document was edited.

Evaluation should match consequence. Important workflow changes can justify a
bounded outcome comparison with comparable starting conditions; do not invent a
failing baseline. Existing traces may suffice for narrower repairs, with their
limits stated. No change is complete merely because more instructions exist.
