<!-- capsule-v2 -->
# Factored verification — generate checks, answer each in isolation, revise from contradictions

**Source:** Veda (`veda-ts`, MIT, `master@f050518c99fa54a5a0af4a04918aaf01d1ed94e1`); Codebase Memory `veda`. **Question:** How does a verifier decompose a draft into independent checks, answer them without the draft (to avoid copying hallucinations), and revise the draft from contradictions — while supporting partial resume?

## Factored verification pipeline
**Path/Symbol:** `src/core/verify.ts:runVerification` (643–743), composed of `runGenerateChecks` (405–429), `runAnswerCheck` (465–494), `runAnswerChecks` (540–626), `runRevision` (749–782).
**Signature:** `runVerification({ backend, model?, systemPrompt, reasoning?, sandbox?, cwd?, type, draft, originalTask, checksOverride?, completedResults?, ... }) → Promise<VerificationResult>`.
**Data Shape:** `Check = { id, question, targetClaim?, difficulty? }`; `CheckResult = { checkId, answer, verdict: 'supports'|'contradicts'|'uncertain', confidence }`; `Revision = { revised, changes[], conflicts[] }`; `VerificationResult = { checks, results, revision?, usage, sessionId? }`. Difficulty maps to reasoning: easy→low, moderate→medium, hard→high.

### Decisive source
```ts
// difficultyToReasoning (verify.ts:21-28)
switch (difficulty) { case 'hard': return 'high'; case 'moderate': return 'medium'; default: return 'low'; }

// runAnswerChecks: parallel, resume via completedResults, fault-tolerant via allSettled
const checksToRun = checks.filter(c => !completedResultsById.has(c.id));
const settled = await Promise.allSettled(checksToRun.map(async => runAnswerCheck({...})));
// fulfilled → keep result; rejected → { verdict:'uncertain', confidence:0.5, answer:`Check failed: ${msg}` }
// results merged in checks order: completedResultsById ?? newResultsById ?? { 'Check not executed', uncertain, 0.5 }

// runVerification step 1: checksOverride ? use it (resume) : runGenerateChecks
// step 2: runAnswerChecks WITHOUT reasoning → each check uses difficultyToReasoning
```

**Flow:** (1) generate checks from the draft (or reuse `checksOverride` for resume); (2) if none, return empty; (3) answer all checks in parallel, each in isolation with NO access to the draft, each reasoning level defaulted from its difficulty; (4) merge completed + new results in check order; (5) optionally `runRevision` with the contradicting results to produce a revised draft.

**Invariant:** each check is answered without the original draft (factored, prevents copying hallucinations); a failed check degrades to `uncertain`/0.5 rather than aborting; resume skips already-answered checks via `completedResults`/`checksOverride` and never re-runs them.

**Probe:** `tests/core/verify-primitives.test.ts` — `parseChecks` (lenient XML, missing-difficulty→easy, skip missing id), `parseSingleCheckResult` (missing confidence→0.7, ID mismatch→uncertain), `runAnswerChecks` resume (all-completed returns results with zero usage; merged results preserve check order). Also `tests/core/verify.test.ts` for `parseCheckResults`/`parseRevision`. Coverage caveat: `tests/` is excluded from the index by design (`fast-pattern`), so these probes are source-grounded from the on-disk test files, not graph-covered.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-ecosystem-veda", query: "runVerification runGenerateChecks runAnswerChecks parseChecks", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the factored verification contract (generate → answer-in-isolation → revise), the difficulty→reasoning mapping, the lenient XML check/result parsing, and the resume semantics. Adapt the prompt wording, backend names, and reasoning-level vocabulary to the host. Omit the judge/winner-rationale internals unless a target needs them.
