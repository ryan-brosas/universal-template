# Essential: Steer Outcomes, Not Behavior (AGENTS.md / System Prompts)

Source: Discord conversation with mentor Tom, 2026-08-11. The complementary
half of the operating philosophy. Treat as an essential.

---

## 1. The Core Principle: Do Not Over-Constrain the Agent

The fundamental architectural error in AI agent engineering is attempting to
micromanage the model's internal cognitive process through restrictive, negative,
or overly rigid system prompts and `AGENTS.md` files.

When an agent is subjected to a wall of behavioral prohibitions ("never do X",
"always think in sequence Y", "avoid speculative abstraction", "grow only in layers"),
its effective reasoning capability collapses.

**The Master Rule: Steer OUTCOMES, not BEHAVIOR.**
- **During Implementation:** Grant the agent complete autonomy to draft code,
  create temporary files, try prototypes, and run exploratory commands.
- **At the Outcome Boundary:** Enforce the highest standards of correctness,
  hygiene, and architectural integrity using **unbypassable mechanical gates,
  compiler checks, and automated CI suites**.

---

## 2. The 4 High-Risk Prompt Drifts & Why They Fail

The following four prompt patterns appear frequently in agent instructions because
they sound like "prudent engineering wisdom." In practice, they are high-risk
anti-patterns that cause severe agent degradation:

### 1. "Choose the simplest implementation that fully meets current requirements. Avoid speculative abstractions, configuration, and indirection."
* **Why it sounds good:** It attempts to prevent over-engineering and YAGNI violations.
* **Why it backfires:** The agent interprets this as a ban on creating helper functions,
  data structures, error classes, or configuration interfaces. It responds by inlining
  giant monolithic 500-line functions, duplicating logic across files, and creating brittle,
  untestable code.
* **Mechanical Outcome Alternative:** Allow modular abstractions during drafting. Run AST
  scanners (`dead-code.py`, `vulture`, `ts-prune`) at the end to prune truly unused
  exports and unreferenced abstractions.

### 2. "Grow the system in layers. Start from the smallest version that works end to end... Never trade a working product for unfinished complexity."
* **Why it sounds good:** It encourages iterative development.
* **Why it backfires:** Real features often require foundational prerequisites (e.g. database
  migrations, auth middleware, protocol codecs) before an end-to-end flow can function.
  The agent gets paralyzed trying to make an incomplete stub "work end-to-end" before building
  its required dependencies.
* **Mechanical Outcome Alternative:** Define explicit API contracts and schema tests.
  Verify with Catch-First end-to-end integration tests once the full feature branch is assembled.

### 3. "Make architectural decisions for the long term. Do not accept a stopgap that only works for now and is meant to be replaced later."
* **Why it sounds good:** It attempts to avoid technical debt.
* **Why it backfires:** It induces severe analysis paralysis. The model refuses to write
  straightforward solutions, hallucinating massive enterprise frameworks, factory patterns,
  and unnecessary abstraction layers to accommodate hypothetical future needs.
* **Mechanical Outcome Alternative:** Keep interfaces narrow and typed. Rely on Schema
  commit boundaries and versioned APIs rather than speculative future-proofing.

### 4. "Study how established products solve the problem before designing a solution. Adopt their proven patterns and conventions rather than inventing an approach from scratch."
* **Why it sounds good:** It seeks to leverage prior art.
* **Why it backfires:** It triggers expensive, unbounded research loops on trivial tasks.
  A simple utility script or regex fix becomes a 30-minute web-browsing excursion looking
  for "established industry patterns."
* **Mechanical Outcome Alternative:** Use Inspiration Gates with local Codebase Memory or
  indexed foundation skills. If no prior art is explicitly requested or indexed, proceed directly
  to implementation.

---

## 3. The Post-Training Degradation Mechanism

Why does behavioral over-prompting degrade modern LLMs?

1. **RLHF Alignment Conflicts:** Modern models undergo extensive Reinforcement Learning
   from Human Feedback (RLHF) to act as helpful, proactive problem-solvers.
2. **Attention Weight Dilution:** Rigid negative rules consume high-priority attention
   weights in the transformer layers, distracting the model from the actual technical domain logic.
3. **Induced Timidity & Refusal Loops:** When bombarded with negative constraints, the model
   becomes overly hesitant. It apologizes repeatedly, asks for permission for routine edits,
   or claims tasks are impossible rather than risking a violation of a vaguely worded prompt rule.
4. **Conclusion:** Sweeping behavioral rules harm the post-training portion of the model.
   Keep `AGENTS.md` focused strictly on repository facts, safety boundaries, and verification commands.

---

## 4. The Complete Translation Matrix: Prompts $\to$ Mechanical Gates

| Behavioral Prompt Mandate (Anti-Pattern) | Mechanical Outcome Enforcement (The Remedy) |
| :--- | :--- |
| *"Write clean code with no trailing spaces or formatting issues."* | the pi-template repo's `scripts/repo-hygiene.py` and `git diff --check` running in pre-commit hooks and CI. |
| *"Never write dead code or unused functions."* | the pi-template repo's `scripts/dead-code.py` parsing AST and symbol references. |
| *"Always maintain consistent skill packs and manifests."* | the pi-template repo's `scripts/check-integrity.py` asserting 1:1 parity between `packs.json` and disk. |
| *"Always format your commit messages properly."* | the pi-template repo's `scripts/conventional-commit.py` and `.github/workflows/pr-title.yml`. |
| *"Ensure your code handles all errors and doesn't crash."* | Compiler strict mode (`tsc --strict`, `mypy --strict`, `cargo clippy`) and typed error channels. |
| *"Make sure you don't break existing tests."* | Automated pytest / vitest test runners in CI. |
| *"Do not touch files outside your assigned task."* | Schema commit guard enforcing rollback on undeclared file modifications. |

---

## 5. The Conclusive PR Loop Playbook

The ultimate expression of steering outcomes is the **Conclusive PR Loop**:

```
[Agent drafts code & runs local checks]
                  │
                  ▼
[1. Commit with Conventional Format]
   git commit -m "feat(scope): descriptive summary"
                  │
                  ▼
[2. Push Branch to Origin]
   git push origin <feature-branch>
                  │
                  ▼
[3. Open Pull Request]
   gh pr create --title "..." --body "..."
                  │
                  ▼
[4. Watch Mechanical CI Gates]
   gh pr checks --watch
                  │
                  ├── (If CI Fails / Bot Reviews) ──► Fix mechanically & push again
                  │
                  ▼
[5. All Checks Green & Comments Resolved]
   gh pr merge --squash --delete-branch
```

By relying on `gh pr checks --watch`, the human operator and agent share an objective,
indisputable definition of "done."
