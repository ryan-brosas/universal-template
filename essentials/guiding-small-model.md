# Essential: Guiding a Small Model (deepseek-flash) — Operating Philosophy

Source: Discord conversation with mentor Tom, 2026-08-21. This is the core
philosophy that drives all our work. Treat it as an essential.

---

## 1. The Core Principle: The Equivalence of Small Models

A small model (e.g., `deepseek-flash`, `deepseek-v4-flash`) is **agentically equivalent**
to a frontier model (`sol`, `fable`, `opus`, `sonnet`). It possesses the same structural
capacity for multi-step reasoning, loop stepping, tool calling, error recovery, and
deterministic execution.

### The Real Difference: Knowledge vs. Capacity
The only fundamental difference between a small model and a massive frontier model is **knowledge volume**:
- Massive frontier models have billions of parameters that have memorized obscure library APIs,
  deprecated SDK patterns, esoteric framework configurations, and thousands of documentation pages.
- Small models lack that encyclopedic memorization. When forced to guess an unfamiliar interface
  or construct glue code from abstract descriptions, they hallucinate or generate plausible-sounding
  but non-existent methods.
- **The Critical Axiom:** You do not try to make the small model "smarter" through prompt gymnastics,
  excessive instructions, or abstract prose.
- **The Core Practice:** You **give it direct, unvarnished ground truth to work from**.

When provided with concrete ground truth (real code, exact signatures, verified invariants,
and named test probes), a small model executes with frontier-grade precision at 10x the speed,
a fraction of the cost, and with zero hallucination.

---

## 2. The Core Rules

### Rule 1: Code is Ground Truth, Not Specs (Docs Come Last)

* **The Pitfall of Markdown Specs:** As Tom explicitly teaches, do not write markdown specifications up-front. The moment you substitute a markdown specification for the actual code (types, imports, test signatures), you strip away the contextual constraints that a model needs to reason accurately.
* **Token Burning & Iteration Hell:** The more you rely on markdown as an abstract spec, the more tokens you burn attempting to "sync" the spec with reality, writing defensive prompts, and resolving discrepancies between what the spec imagined and what the runtime requires.
* **The Solution (Docs After Implementation):** The working code, with its types and tests, is the only decisive source of truth. Markdown documentation (architectural overviews, API docs, usage guides) should only be generated **after** the implementation is complete, treating the codebase as the ground truth. Let the architecture emerge from the behavior, then project the docs.
* **Session as Artifact:** The active chat session is already a living artifact. Only burn
  decisions into persistent markdown when you expect a multi-day or multi-agent run.

### Rule 2: The Reusable Unit is the Skill (The Shortcut), Not the Spec
> *"Deepseek makes no mistakes, because the workflow is written in code or a skill somewhere."*
* When a complex procedure or interface pattern is encoded in a skill or foundation capsule,
  the small model does not need to re-derive logic from first principles.
* It reads the decisive source, follows the verified flow, respects the invariant,
  and confirms against the named probe.
* The skill acts as an unbypassable shortcut that guarantees deterministic correctness.

### Rule 3: Prewalk is Your Best Tool
* Prompt planning phases matter, but **not to micromanage or plan every step by hand**.
* Do not write rigid step-by-step instructions telling the agent how to think or sequence basic tasks.
* Give the agent deep repository context (file trees, symbol relationships, graph dumps)
  and let it **search the context**. The agent will prewalk the graph and discover the seams itself.

### Rule 4: Squeeze to the Last Drop (Skimming vs. Understanding)
* **The Skimming Trap:** Skimming a 30,000-line codebase surfaces 3–6 obvious functions.
  This creates shallow, brittle skills that fail under real edge cases.
* **True Understanding:** True understanding sweeps module by module through helper files,
  utility libraries, decorators, and internal data structures.
* **Case Study — `graphiti` (36,684 lines):**
  * *Pass 1 (Skim):* Found 6 surface-level seams.
  * *Pass 2 (Deep Squeeze):* Found 16 critical hidden seams:
    * `search_utils.py` (2,048 lines) $\to$ RRF fusion, MMR rerankers, BFS similarity matrices.
    * `bulk_utils.py` $\to$ UnionFind path compression and pointer rewriting.
    * `decorators.py` $\to$ Group fan-out and versioned prompt decorators.
    * `tracer.py` $\to$ Unified NoOp and OpenTelemetry span abstractions.
* **The Squeeze Contract:** Every module in a target codebase must either become a
  `<!-- capsule-v2 -->` reference OR receive an explicit `omit-with-reason` in the work record.
  Never silently skip a subsystem.

---

## 3. The Two-Pass Learning Protocol

For complex repositories and foundational systems, execute the following structured protocol:

```
┌─────────────────────────────────────────────────────────────┐
│ PASS 1: Exploration & Subsystem Mapping                     │
│ 1. Map full directory & package hierarchy                   │
│ 2. Identify major subsystems, boundaries, and dependencies  │
│ 3. Read core interface files & orchestrators slowly         │
│ 4. Author initial high-level foundation capsules            │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ PASS 2+: Seam Extraction & Internal Dissection              │
│ 1. Re-enter SAME repo using NEXT-PASS TARGETS as entries   │
│ 2. Deep-dive internal utilities, helpers, and decorators    │
│ 3. Extract exact line ranges, signatures, and flow invariants│
│ 4. Author deep <!-- capsule-v2 --> references                │
│ 5. Sample and cite direct tests as verification probes      │
└─────────────────────────────────────────────────────────────┘
```

### Pass Guidelines:
- Repositories $<10\text{k}$ lines: 1–2 passes.
- Repositories $10\text{k}–50\text{k}$ lines: 2–3 passes.
- Repositories $>50\text{k}$ lines (e.g. `browser-use`, `graphrag`, `nocodb`): 3+ passes.
- **Never switch repositories prematurely.** Complete depth on one asset beats shallow breadth across ten.

---

## 4. The `<!-- capsule-v2 -->` Standard Contract

Every foundation reference extracted from code must conform to the canonical capsule-v2 specification:

1. **Header Marker:** `<!-- capsule-v2 -->` on line 1.
2. **Title & Question:** Clear H1 describing the capability, followed by the exact porting question:
   `**Source:** <repo> <commit>; Codebase Memory <project>. **Question:** <How does X solve Y without Z?>`
3. **Sections:**
   - `**Path/Symbol:**` File path and line numbers at verified commit.
   - `**Signature:**` Exact TypeScript/Python/Rust type signatures.
   - `**Data Shape:**` Input and output data contracts.
   - `### Decisive source:` Verbatim code excerpt read during the active session.
   - `**Flow:**` Step-by-step state progression ($A \to B \to C$).
   - `**Invariant:**` Non-negotiable structural rules that must not be broken.
   - `**Probe:**` Direct test path and line range proving behavior.
   - `## Get live surrounding code:` Exact `codebase_memory` search query.
   - `## Verdict:` Adopt/Adapt/Omit verdict with explicit provenance and caveats.

---

## 5. What This Means for Our Setup

- **Foundation Skill Packs (`pack-foundations`):** Squeeze external inspiration repositories
  into canonical `<!-- capsule-v2 -->` foundation skills so `deepseek-flash` can lift proven
  code instead of inventing unverified solutions.
- **Retrieval Maps over Specs:** Use skill leaves as retrieval maps pointing to decisive source code.
- **Continuous Learning & Persistence:** Record every pass, mined seam, and unmined target in the
  durable work record (`research.md`) so learning compounds across sessions and cron runs.
