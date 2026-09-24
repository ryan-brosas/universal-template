---
title: leverage-capture
summary: 'Use when a concrete lesson may improve future work: choose its natural owner or no permanent change after understanding the evidence. Not an automatic session-closing ritual.'
kind: playbook
---

# Choose where experience should change work

## Qualification before destination

Start with the lesson, not an artifact. What future action or outcome should change,
under which conditions, and why does the experience support that change? Consider
successful techniques as well as failures. A one-time observation may be disposable;
a single expensive failure, durable user correction, or strong success may be enough.
Recurrence is evidence, not an admission requirement.

Do not preserve retrievable code inventories. Source, tests, documentation, Git,
Sourcebot, and GitHub can recover repository facts. Experience can preserve judgment
those facts alone do not reproduce: diagnostic order, comparison strategy, recovery,
implementation tradeoffs, and verification techniques.

This procedure selects a destination for an understood candidate. For full session
learning, use [session improvement](../session-improvement-compiler/README.md).
Reflection can recommend changes but does not authorize mutation. Adopt only within
the task's granted scope; explicit learning permission is not machine-wide permission.
When session compilation invokes owner selection, its deliverable is the reusable
method; a code or configuration repair the lesson also suggests is a separate
finding that needs its own authorization.

## Match responsibility, then find its owner

The following are alternatives, not a ranking:

| Desired change | Natural owner and useful check |
|---|---|
| Implementation handles a case correctly or removes repeated work | Owning code/module; test its consumer and relevant behavior |
| Integration uses the right setting or registration | Owning configuration; exercise the integration, not just parsing |
| A deterministic regression is prevented | Relevant test/check with useful signal and acceptable false positives; fix implementation too when needed |
| Future reasoning can reuse a technique, sequence, or boundary | Fitting playbook/skill; test discovery and application from the actual task |
| Invocation reliably communicates intent or scope | Existing prompt/router; try a fresh representative request |
| A local decision or constraint would otherwise be lost | Existing project decision/docs/configuration owner; verify its affected workflow can find and respect it |
| A task needs a source reference or design capture | Existing reference contract, only for an actual reuse need, not to archive the session |
| Evidence is weak, value small, transient, or already retained | No permanent change; explain a material uncertainty or deferral without creating a tracking artifact |

Search for the narrowest existing owner *after* choosing the responsibility. Reuse
one that genuinely fits. If none fits and the lesson merits adoption, create a small
owner discoverable from the relevant task; do not cram it into an unrelated skill.
A candidate can require complementary code, configuration, and tests rather than
one forced classification. Do not substitute a global prohibition for a local fix.

## Retain only enough

The maintenance cost should justify the avoided rediscovery or improved outcome.
Preserve concrete decisions and exceptions, not generic advice. Project-specific
choices stay with the project. Speculative explanations remain qualified; a safe,
observed technique can be adopted without pretending its cause is settled.

Skill/playbook candidates follow [writing-skills](../writing-skills/README.md).
References follow [the reference contract](../reference-driven-development/references/contract.md).
Necessary project recovery state follows [goal-setup](../goal-setup/README.md), not a
new session-memory system. No permanent change can be the correct outcome, but it
must not conceal an unfinished qualified repair. Name concrete blockers and continue
with authorized changes.

## Verify adoption

Exercise the owning behavior and consumer with checks appropriate to the change.
For procedures, start from the future task, find the method, and apply it; an orphan
file is only saved. Test important boundaries without fixed pass counts or invented
baseline failures. Use existing tests where they fit; do not create validation
machinery to justify writing guidance.

Report saved, adopted, and shown useful separately where the distinction matters.
A working implementation or a successful representative task is stronger evidence
than a file's existence. No speed or quality improvement is measured unless it was
actually compared.
