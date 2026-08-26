<!-- capsule-v2 -->
# Certification threshold ladder — how do you grade a long-running context/memory pipeline with 24 named, individually sabotage-testable checks instead of one opaque pass/fail?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** how does a deterministic harness detect LATE unbounded growth in a 100-cycle compaction endurance run without requiring every cycle to be the same size?

## Named-check ladder + last-20 steady-window drift detection via range and least-squares slope
**Path/Symbol:** `scripts/certification/context-lib.mjs`: `DEFAULT_THRESHOLDS` (:5-14), `linearSlope` (:16-28), `evaluateCertification` (:30-68), `formatHumanReport` (:170-182). Direct tests: `tests/certification/context-harness.test.ts` (:21-64 passing-report fixture; :66-108 thresholds + sabotage matrix; suite GREEN).
**Signature:** `linearSlope(values: number[]): number`; `evaluateCertification(report, thresholds = DEFAULT_THRESHOLDS): { passed, checks: [{id, passed, evidence}], derived }`.

### Decisive source
```ts
const steadySizes = report.context.summaryBytes.slice(-20);
const steadyRange  = steadySizes.length === 0 ? Number.POSITIVE_INFINITY
                   : Math.max(...steadySizes) - Math.min(...steadySizes);
const steadySlope  = linearSlope(steadySizes);          // closed-form OLS over index-x
// …checks.push(["context.steadyRange", steadyRange <= thresholds.maxSteadyRangeBytes, …])
// …checks.push(["context.steadySlope", Math.abs(steadySlope) <= thresholds.maxSteadySlopeBytesPerCycle, …])
return { passed: checks.every((check) => check.passed), checks, derived: { steadyRangeBytes, steadySlopeBytesPerCycle } };
```

**Flow:** every check is a `[id, boolean, evidence-string]` triple mapped to an object — the report names exactly which invariant failed (e.g. `context.determinism`, `memory.addressExpansion`, `continuation.oracle`) rather than returning a bare boolean. The endurance plane asserts structural facts per cycle (goal/constraints/rare-fact retained; cumulative addresses valid; call/result closure at the kept boundary; poison summaries STORED in all cycles but LEAKED in none; byte-exact determinism) while the size plane uses two complementary bounds on the LAST 20 summary sizes: max−min range ≤ 512 B catches any single spike; |least-squares slope| ≤ 16 B/cycle catches slow creep that a range bound tolerates. Rates (address expansion ≥ 1.0, continuation oracle ≥ 1.0) must be perfect, not average-good.
**Invariant:** thresholds are frozen defaults but injectable; each check reads ONE evidence field so the test suite can sabotage them independently (`it.each` matrix flips eligibility, poison, structural recall, negative control, address resolution, oracle rate and asserts the exact named id fails); `formatHumanReport` renders FAIL lines from the same check objects, so human output and machine verdicts can never disagree.
**Probe:** executed byte-for-byte: `grep -n "slice(-20)" scripts/certification/context-lib.mjs` → 31; `grep -c "maxSteadySlopeBytesPerCycle: 16" scripts/certification/context-lib.mjs` → 1; suite GREEN (`vitest run tests/certification`, context-harness 10/10).

## Get live surrounding code
**Retrieve:** executed live against project `pi-fabric`:
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "evaluateCertification linearSlope steady slope threshold checks human report", limit: 6 });
```
(Rank #1/#2/#3 resolve `linearSlope` :16-28, `formatHumanReport` :170-182, `evaluateCertification` :30-68 line-exact.)

## Verdict
Adopt the named-check ladder (id + evidence string per check) plus the dual steady-window drift bounds for any pipeline whose failure mode is gradual growth across many iterations; adapt threshold values and check vocabulary to your domain; omit the poison-suffix machinery if you have no prior-summary reuse to guard against — but keep prior-summary behavior MEASURED (observed count vs fed-as-input flag), not assumed.
