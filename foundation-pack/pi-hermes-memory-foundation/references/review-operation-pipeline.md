<!-- capsule-v2 -->
# Review operation pipeline — "nothing to save" short-circuit, lenient parse / strict apply, and the atomic-vs-best-effort fork

**Source:** pi-hermes-memory (MIT, `main@26f0acaa7741a81ea28eb992ab7ffcfdb7b50a0c`); Codebase Memory `pi-hermes-memory`. **Question:** An LLM returns free text that may contain memory-operation JSON — where do you tolerate junk, and where do you refuse?

## parseReviewOperations
**Path/Symbol:** `src/handlers/review-memory-ops.ts` — `parseReviewOperations` (:231–262), salvage ladder `extractJsonPayload` (:182–212: raw JSON.parse → fenced ```json block → FIRST `{` to LAST `}` slice), per-op field filters (`isReviewAction`/`isReviewTarget` :223–229, `isMemoryCategory` :214–221), "nothing to save" gate (:232–234).
**Signature:** `parseReviewOperations(text: string) → ReviewMemoryOperation[] | null` — `[]` = explicit no-op, `null` = unparseable.
**Data Shape:** accepted op = `{action ∈ add|replace|remove, target ∈ memory|user|project|failure, content?, old_text?, category?, failure_reason?}`; ops failing action/target validation are DROPPED silently (not rejected) during parse.

### Decisive source
```ts
if (/nothing to save/i.test(text) && !text.includes("{")) return [];   // model's polite decline ≠ parse failure
const payload = extractJsonPayload(text);
if (!payload || typeof payload !== "object" || Array.isArray(payload)) return null;
const operations = (payload as { operations?: unknown }).operations;
if (!Array.isArray(operations)) return null;
```
The `{`-containment guard makes the order safe: a decline message that QUOTES a JSON example is parsed (and then likely fails cleanly), never mistaken for a no-op.

## applyReviewOperations
**Path/Symbol:** same file :264–403. Atomic mode (`options.requireAtomicShrink`) validates the WHOLE plan first: non-empty (:276–282), exactly one target across all ops (:284–291), expected-target match when given (:292–298), project store present for project targets (:299–305) — then delegates to `applyMutationPlan(..., {requireShrink: true})`; any failure ⇒ `{appliedCount: 0, skippedCount: operations.length}` (:318–324). Best-effort mode loops ops individually, skipping empty-content/missing-old_text items and unavailable project targets, counting `appliedCount/skippedCount`.
**Data Shape:** target translation table — `"project"` maps to the PROJECT store with internal target `"memory"`; failure adds default `category ?? "failure"` and stamp `projectName` (:309–316, :347–353).

**Flow:** responseText extraction → parse (lenient about envelope junk) → apply (strict about semantics). The two modes are chosen by the CALLER's context: consolidation passes requireAtomicShrink so a review can never grow memory; direct save paths use best-effort so one bad op doesn't discard good ones.
**Invariant:** parse-lenient/apply-strict is a deliberate split — salvaging JSON from chatty LLM output is free, but semantic validation (targets, atomicity) must happen at the store boundary where typed errors exist. In atomic mode skippedCount === operations.length on ANY failure, preserving count symmetry for callers computing rates.
**Probe:** `tests/handlers/review-memory-ops.test.ts` — "parses valid JSON operations" (:216), "extracts JSON from fenced blocks" (:236), "rolls back the entire atomic plan when a later operation fails" (:290), "rejects mixed and unexpected atomic targets before mutation" (:322), "returns an actionable direct-completion error without partial atomic changes" (:529).
**Retrieve:** `search_graph({ project: "pi-hermes-memory", query: "parseReviewOperations extractJsonPayload applyReviewOperations requireAtomicShrink", limit: 5 })`

## Verdict
Adopt wherever an LLM reply drives structured store mutations. Adapt the op schema and decline phrase; keep the three-tier JSON salvage, silent-drop type filtering at parse, and the validate-whole-plan-then-delegate atomic mode. Omit nothing.
