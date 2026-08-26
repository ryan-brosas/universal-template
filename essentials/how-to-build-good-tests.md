# Essential: How to Build Good Tests and Gates

Source: Discord conversation with scarywood75, 2026-08-03. A practical
methodology for building the mechanical enforcement from Pillar 4. Treat as an
essential.

---

## 1. The Core Principle: The Catch-First Axiom

> *"A test is only a good test if it can properly CATCH — a passing test means nothing."*

The most pervasive illusion in software engineering and AI testing is believing that
a suite of passing tests guarantees correctness. If a test passes when run against buggy,
incomplete, or broken code, that test is completely useless: it produces false security
while consuming compute time.

---

## 2. The 5-Step Catch-First Protocol

To prove that a test is a genuine catch, adhere strictly to the **Catch-First Protocol**:

```
[Step 1: Identify Defect or Missing Capability]
                       │
                       ▼
[Step 2: Author the Catch Test]
(Assert expected behavior, error codes, and invariants)
                       │
                       ▼
[Step 3: Run against Pre-Fix State -> MUST FAIL RED!]
(Verify the test fails with the EXACT expected failure signature)
(If it passes unexpectedly -> REWRITE TEST; it is invalid)
                       │
                       ▼
[Step 4: Apply the Implementation / Fix]
(Write the minimal code necessary to resolve the failure)
                       │
                       ▼
[Step 5: Run against Post-Fix State -> MUST PASS GREEN!]
(Verify clean execution and absence of regressions)
```

Only when **Step 3 (RED)** and **Step 5 (GREEN)** both succeed is the test proven to be a true catch.

---

## 3. Broad Category Testing vs. Narrow Unit Tests

Do not fall into the trap of writing thousands of brittle micro-tests testing hardcoded
strings or static parameters.

**Target the CATEGORY or CLASS of defect:**
- **Broad Test Pattern:** A test harness that asserts that *all* HTTP endpoints return
  a standardized JSON error envelope (`{"error": "...", "code": 401}`) upon unauthorized access.
- **Narrow Test Anti-Pattern:** 50 separate test files testing `test_user_endpoint_auth()`,
  `test_billing_endpoint_auth()` with copy-pasted assert lines.

A single broad test covering an entire architectural invariant provides vastly superior
protection with a tiny fraction of the maintenance burden.

---

## 4. Expand, Don't Duplicate (Preventing Test Bloat)

When an edge case or bug escapes into review or production:
* **The Anti-Pattern:** Immediately create `test_bug_fix_issue_482.py` with custom mock stubs.
* **The Correct Pattern:** Locate the existing test suite that *should* have caught this bug,
  and **EXPAND its parameter matrix or invariant assertions**.

### Benefits of Expansion:
- Keeps the test suite compact, fast, and easy to run in CI.
- Forces your core test harnesses to become more general, resilient, and comprehensive.
- Eliminates the cognitive fatigue of maintaining hundreds of orphaned test files.

---

## 5. Maintaining a Live Test Ledger

Maintain a visible, active ledger of all test suites and the specific bug classes they prevent:
- Document what each test suite owns (e.g. schema validation, concurrency safety, auth boundaries).
- When a new defect surfaces, consult the ledger to identify the blind spot, and assign
  the expanded test case directly to the owning suite.

---

## 6. Testing the Test Units

Your test infrastructure must meet the same architectural standards as production code:
- **No Tautological Mocks:** Never mock the exact domain logic or calculation you are attempting
  to test. Mock only external IO/network boundaries; let domain logic run hermetically.
- **No Static Value Traps:** Use parameterized inputs, fuzzing, and randomized seeds to prevent
  tests from passing only on lucky hardcoded values.
- **Hermetic & Independent:** Tests must never depend on execution order, network access,
  or environment-specific clocks.

---

## 7. The 4-Stage Promotion Pipeline

Transform manual human catches into automated, permanent assets:

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Manual Catch in Review or Pair Programming               │
│    - Human reviewer spots a subtle bug or formatting error. │
├─────────────────────────────────────────────────────────────┤
│ 2. Scratch Script / CLI Probe in the project's `scripts/`        │
│    - Write a fast Python/Bash script that detects the error.│
├─────────────────────────────────────────────────────────────┤
│ 3. Mechanical Test Suite / Pre-Commit Hook                  │
│    - Formalize into a reusable validator with exit codes.   │
├─────────────────────────────────────────────────────────────┤
│ 4. Automated CI Gate with Autofix                           │
│    - Run on all PRs in GitHub Actions; auto-resolve drift.  │
└─────────────────────────────────────────────────────────────┘
```

---

## 8. The Fallacy of GitHub Stars

> *"Using a GitHub repo (stars) is NOT the proper way to judge good code."*

Popularity is social proof, not technical evidence:
- Massive repositories with tens of thousands of stars often suffer from severe technical debt,
  leaky abstractions, and fragile test suites.
- **The Proper Standard:** Define the exact functional outcomes, performance budgets,
  and failure boundaries your project requires.
- Formulate your own verifiable mechanical tests based on ground truth, not external popularity.

---

## 9. Structural Practices for Agentic Development

- **Keep Files Small (<300 lines):** Smaller files reduce token consumption, eliminate merge
  conflicts, and drastically improve LLM comprehension.
- **Group Changes into Cohorts:** Deconstruct large migrations into coherently-themed cohorts
  (e.g., Cohort 1: Types, Cohort 2: Store, Cohort 3: UI). Smaller scopes yield high one-shot pass rates.
- **Build CLI Tools for Everything:** Instead of pleading with an LLM in a prompt to format
  code correctly, provide a CLI tool (e.g. the pi-template repo's `scripts/repo-hygiene.py` at `~/.agents (absorbed from the retired pi-template repo)`) that outputs actionable
  error lines and non-zero exit codes.
