# Essential: Stack Your Leverage — Code is Your Asset

Source: Discord conversation with mentor Tom, 2026-07-26. The third pillar of
the operating philosophy. Treat as an essential.

---

## 1. The Core Principle: Code You Hold is Valuable

> *"Code from scratch is cheap; code you hold is valuable."*

Generating code from zero is a low-cost commodity. The compounding advantage
belongs to the developer who **holds, organizes, and stacks proven code and
procedures** — every hard-won solution that is frozen into a reusable asset
eliminates that class of problem from future work.

## 2. What to keep: classify by representation, not by project

The unit of leverage is a **representation asset** — something that replaces
re-derivation with retrieval. Decide what to keep by what it represents:

| Class | What it is | Keep when | Typical form |
|---|---|---|---|
| **Procedure** | How to reliably do a hard thing | Recurs across sessions/projects; failure is expensive | Skill with a named probe |
| **Reference** | Where a proven implementation lives | You will port or compare against it again | `reference/<repo>/` checkout, pointer note |
| **Mechanism** | A deterministic check that prevents a bug class | The bug can recur silently | Gate script + CI wiring |
| **Experience** | Why an approach failed; what was tried | Expensive to reconstruct; not in any codebase | Session note, OpenViking entry |
| **Working code** | A solved implementation itself | It IS the deliverable | The codebase, versioned |

Do **not** promote by default: a one-off quirk already documented in the fix's
tests or a repo note stays in code. Promotion is earned when the asset would
be re-derived — at real cost — without it.

## 3. Good Output vs. Perfect Code

Do not delay capturing because code is not "academically perfect". You need a
**proven, working good output**, then generalize underneath it without
changing behavior:

> *"This output we have looks really good. Help me improve and generalize the
> code for it, while preserving the exact design output and behavior we have
> today."*

## 4. Post-session capture, with a promotion threshold

At the end of an intensive session, run a capture pass — then promote only
what passes the table above:

1. Recall what the session covered; list candidate assets by class.
2. Promote **recurring edge cases and verified recovery patterns** — the basic
   happy path is easily regenerated; the edge cases took real debugging.
3. Package each promotion in its native form (skill, gate, reference note) —
   not everything becomes a skill.

## 5. The compounding effect

Held assets shorten future work: a fresh problem becomes a pattern match, a
pattern match becomes a retrieval. The mentor's shorthand — 2 hours → 20
minutes → 30 seconds — describes the direction, not a schedule. The test of a
stacked asset is simple: the next task that hits its problem class should cost
notably less than the first one did.
