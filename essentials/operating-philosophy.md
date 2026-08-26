# Essential: The Operating Philosophy (Synthesized)

A unified synthesis of mentor Tom and scarywood75's core operating pillars,
distilled into an authoritative, actionable guide for coding agents and developers.

---

## The Master Axiom

> **Give the small model ground truth (code definitions + skill shortcuts), let it execute freely without behavioral micromanagement, verify outcomes with unbypassable mechanical gates, and stack every hard-won output into permanent skills so leverage compounds exponentially.**

---

## 🏛️ Pillar 1: Code is Ground Truth, Skills are the Shortcuts
*Source: Mentor Tom (2026-08-21)*

1. **Small Model Equivalence:** Small models (`deepseek-flash`) are agentically equal
   to frontier models; they only lack domain knowledge. Feed them concrete code rather
   than prompt fluff.
2. **Code Over Markdown Specs (Docs Come Last):** Markdown specs discard type definitions and burn tokens. As Tom explicitly teaches: *do not write markdown specifications up-front*. Markdown docs should only ever be generated *after* the implementation is complete, derived directly from the working, proven code. The code is the source of truth; docs are just a downstream projection of it.
3. **Skills Guarantee Correctness:** *"Deepseek makes no mistakes, because the workflow
   is written in code or a skill somewhere."* A verified skill eliminates re-derivation.
4. **Prewalk Over Micromanagement:** Give the agent deep repository context and let it
   prewalk the code graph; never hand-plan every trivial step.
5. **Squeeze to the Last Drop:** Deep understanding requires sweeping every internal
   module, helper, and decorator. Use the **Two-Pass Learning Protocol** (Pass 1: Subsystem mapping, Pass 2+: Seam extraction).

---

## 🎯 Pillar 2: Steer Outcomes, Not Behavior
*Source: Mentor Tom (2026-08-11)*

1. **The Anti-Pattern of Behavioral Prompts:** Rigid rules in system prompts ("simplest implementation",
   "grow in layers", "long-term architecture") sound good on paper, but over-constrain the model
   and degrade its post-training problem-solving capacity.
2. **Let the AI Rampage:** Grant the agent full autonomy during the implementation loop.
3. **Enforce Boundaries at the End:** Validate the code at the outcome boundary using automated
   linters, typecheckers, and test suites.
4. **The Conclusive PR Loop:** Push to branch $\to$ open PR $\to$ `gh pr checks --watch` $\to$
   resolve mechanical feedback $\to$ merge when green.
5. **Verifiable Code Taste:** Convert aesthetic principles into deterministic AST metrics and linter rules.

---

## 💎 Pillar 3: Stack Your Leverage (Code is Your Asset)
*Source: Mentor Tom (2026-07-26)*

1. **Code You Hold is Gold:** *"Code from scratch is cheap; code you hold is valuable."*
   One good component becomes a permanent design token.
2. **The Compounding Velocity Curve:** $2\text{ hours}$ (scratch) $\to 20\text{ minutes}$ (pattern) $\to 30\text{ seconds}$ (stacked skill).
3. **Good Output Over Academic Perfection:** Preserve working output; generalize the code
   underneath without breaking the user experience.
4. **Post-Session Skill Capture:** Always run a skill-capture pass at session close:
   > *"Recall what we've done and capture everything into skills in a separate folder... capture all small stuff and edge cases."*
5. **The Leverage Loop:** Master a complex domain $\to$ repeat 2–3 times for edge cases $\to$
   freeze into skills $\to$ deploy for high-value automation.

---

## ⚙️ Pillar 4: Enforce Code Quality Mechanically
*Source: scarywood75 + Tom (2026-07-19)*

1. **Automate All Determinism:** Dead code, dangling exports, missing constants, and duplicate
   logic belong in automated scripts, not prompts.
2. **Prompting for Discipline Fails:** Prompts are suggestions that decay with context length.
   Unbypassable gates are physical laws.
3. **The Infinite Iteration Principle:** *"Given enough attempts against an unbypassable gate,
   the LLM has no choice but to improve the code until it passes."*
4. **Universal & Language Quality Packs:** Deploy universal hygiene/security gates across all
   repos, supplemented by language-specific type and borrow checkers.

---

## 🧪 Test & Gate Methodology: Catch-First Verification
*Source: scarywood75 (2026-08-03)*

1. **The Catch-First Rule:** *"A test is only a good test if it can properly CATCH — a passing test means nothing."*
   Always verify **un-fixed (RED)** $\to$ **fixed (GREEN)**.
2. **Broad Category Testing:** Target bug classes (e.g. all auth failures, all connection leaks)
   rather than single mock instances.
3. **Expand, Don't Duplicate:** When a bug escapes, broaden the existing test unit instead of
   multiplying test files.
4. **Tool Promotion Lifecycle:** Scratch Script $\to$ CLI Command $\to$ CI Gate $\to$ Autofix.
5. **Ignore GitHub Stars:** Judge code by your own mechanical criteria, not popularity.

---

## 🔄 The Complete Development Flywheel

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Ground Truth & Prewalk                                   │
│    - Read real code & symbols (Codebase Memory / local graph)│
│    - Load verified skill shortcuts                          │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Unconstrained Autonomous Execution ("Let It Rampage")   │
│    - Rapid drafting, modular prototyping, direct iteration │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Catch-First Verification & Mechanical Gates              │
│    - RED -> GREEN test validation                           │
│    - Local gates (integrity, hygiene, dead-code, quality)   │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Conclusive PR Loop                                       │
│    - Open PR -> gh watch CI -> resolve feedback -> merge     │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Post-Session Skill Capture                               │
│    - Harvest edge cases -> write capsule-v2 -> stack leverage│
└─────────────────────────────────────────────────────────────┘
```
