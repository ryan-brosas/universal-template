# Essential: Enforce Code Quality Mechanically, Not by Prompting

Source: Discord conversation with scarywood75 + Tom, 2026-07-19. The fourth
pillar of the operating philosophy. Treat as an essential.

---

## 1. The Core Principle: Automate Everything Deterministic

> *"Anything that is mechanical, predictable, or deterministic — create tests for it."*

The single greatest point of failure in AI-driven software development is relying
on LLMs to maintain discipline, remember formatting rules, or catch their own errors
through prompting alone.

LLMs are probabilistic token predictors. Over long, complex sessions, they suffer
from context dilution, probability decay, and attention degradation.

**The Solution:**
- Completely remove mechanical, deterministic responsibilities from the LLM.
- If a standard can be expressed as a regex, an AST traversal, a compiler check, a linter,
  or a unit test, **encode it into an unbypassable mechanical gate**.
- When an automated gate fails, feed the error output back to the model:
  > *"Given enough attempts against an unbypassable mechanical gate, the LLM has no choice but to improve the code until it passes."*

---

## 2. Why Prompted Discipline Fails

Relying on system prompts or user instructions to enforce discipline fails due to three
fundamental AI behaviors:

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Prompt Suggestions Decay with Context Length             │
│    - As context grows to 50k+ tokens, system prompt weights │
│      compete with immediate tool outputs and conversation.  │
├─────────────────────────────────────────────────────────────┤
│ 2. The Illusion of Compliance (Hallucinated Self-Checks)    │
│    - When asked "Did you check for unused imports?", the LLM│
│      readily responds "Yes, all checked" without running    │
│      a single AST probe.                                    │
├─────────────────────────────────────────────────────────────┤
│ 3. Rationalized Shortcuts                                   │
│    - Under context pressure, the model rationalizes skipping│
│      un-enforced steps to reach a quick conclusion.         │
└─────────────────────────────────────────────────────────────┘
```

**The Law:** Never prompt for something that can be verified mechanically. Build a gate.

---

## 3. The 4 Deterministic Defect Categories

Automate detection for these four deterministic defect categories across every project:

### 1. Dangling & Dead Symbols
* **What it is:** Functions, classes, variables, or types declared and exported but never
  called anywhere in the repository.
* **Why it happens:** AI agents frequently draft speculative helper methods and forget
  to wire them.
* **Mechanical Solution:** AST dead-code analysis (e.g. the pi-template repo's `scripts/dead-code.py` at `/home/utopia/work/project/pi-template`, `ts-prune`, `vulture`).

### 2. Broken Contracts & Missing Constants
* **What it is:** Code referencing deprecated keys, renamed configuration parameters,
  or missing enum values.
* **Why it happens:** The model relies on outdated pre-training knowledge for library structures.
* **Mechanical Solution:** Strict static typecheckers (`tsc --strict`, `mypy --strict`, `cargo check`).

### 3. Dangling Imports & Manifest Drift
* **What it is:** Unused import statements, missing package dependencies, or untracked skills.
* **Why it happens:** Rapid editing leaves abandoned import statements.
* **Mechanical Solution:** Linter passes (`ruff`, `biome`, `check-integrity.py`).

### 4. Near-Duplicate Code & Fork Drift
* **What it is:** Slightly altered clones of existing utility functions.
* **Why it happens:** The model reinvents a helper rather than discovering an existing one.
* **Mechanical Solution:** Semantic and prefix similarity checkers (e.g. `quality-gate.py`'s
  near-duplicate description detector).

---

## 4. Unbypassable Gates vs. Suggestions

| Workflow Requirement | Prompted Suggestion (Fails) | Unbypassable Mechanical Gate (Succeeds) |
| :--- | :--- | :--- |
| **Research Before Mutation** | *"Please make sure you thoroughly search the docs before editing."* | Workflow state machine rejects `write_to_file` until a verified research evidence log is written to disk. |
| **Mutation Scope Boundary** | *"Only touch the files relevant to this task."* | Schema guard (`schema.verify` $\to$ `schema.commit`) rolls back any transaction touching undeclared files. |
| **Formatting & Whitespace** | *"Format code nicely with clean line endings."* | `repo-hygiene.py` and `git diff --check` running in CI and pre-commit hooks. |
| **Commit Subject Standards** | *"Use conventional commit formatting."* | `conventional-commit.py` and `pr-title.yml` failing PR checks on non-conventional titles. |

---

## 5. Universal vs. Language-Specific Quality Packs

Organize all mechanical enforcement into a two-layer hierarchy:

```
┌─────────────────────────────────────────────────────────────┐
│ LAYER 1: Universal Quality Pack (Language-Agnostic)         │
│ ├── Trailing whitespace & EOF newline checking              │
│ ├── UTF-8 encoding validation                               │
│ ├── Automated secrets & credential pattern scanning         │
│ ├── Conventional commit & PR title validation               │
│ └── Git diff whitespace integrity (git diff --check)        │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ LAYER 2: Language-Dependent Quality Packs                   │
│ ├── TypeScript: strict nulls, Effect-TS typed errors, no any│
│ ├── Python: pytest + hermetic fixtures, mypy strict, ruff   │
│ ├── Rust: cargo clippy -- -D warnings, cargo audit, borrowck│
│ └── Go: golangci-lint, go vet, staticcheck                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. What This Means for Our Setup

- **Standard Mechanical Suite (pi-template repo `scripts/`):** The repo at
  `/home/utopia/work/project/pi-template` provides `check-integrity.py`,
  `quality-gate.py`, `dead-code.py`, `repo-hygiene.py`, and `conventional-commit.py`.
- **Zero Prompted Discipline:** The slash-command prompts (`.pi/prompts/`) do not plead
  with the model to be careful; they require executing deterministic commands and inspecting output.
- **CI is the Ultimate Judge:** GitHub Actions (`.github/workflows/`) provides an objective,
  reproducible pass/fail verdict for every single commit.
