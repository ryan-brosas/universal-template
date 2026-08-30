<!-- capsule-v2 -->
# SARIF → platform output projection — how does one report become three native formats without losing the severity contract?

**Source:** qodana-action Apache-2.0 `main@e0675fbe…`; Codebase Memory `qodana-action`. **Question:** A tool emits SARIF. How do you project it into GitHub Check annotations, a markdown PR comment, and a job summary — with which filtering and level mapping? (Refreshed at e0675fb: scan-side parseResult now resolves URI bases first — see `sarif-uri-base-resolution`; the common/ variant still emits the raw artifact uri.)

## Baseline filtering, level ladder, rule-description join, 50-cap batching
**Path/Symbol:** shared parse `common/output.ts:parseSarif` (:75+) + `parseResult` (:106+); annotations `scan/src/annotations.ts:parseSarif` (:168-201), `parseResult` (:124-161 — since e0675fb resolves `originalUriBaseIds` before reading the region; see `sarif-uri-base-resolution`), `publishAnnotations` (:56+), `getGitHubCheckConclusion` (:206+), `toAnnotationProperties` (:228+).
**Signature:** `parseSarif(path)` → `{title, summary, text, problemDescriptions|annotations}`; `publishAnnotations(name, problems, failedByThreshold, execute)`.
**Data Shape:** SARIF `runs[0]`; rules from `tool.driver.rules` + `tool.extensions[].rules` via `common/utils.ts:parseRules` (:71-91; fullDescription prefers `.markdown` over `.text`).

### Decisive source
```ts
problemDescriptions = run.results
  .filter(result =>
    result.baselineState !== 'unchanged' &&
    result.baselineState !== 'absent'
  )
  .map(result => parseResult(result, rules))
  .filter((a): a is ProblemDescriptor => a !== null && a !== undefined)
// level ladder (both variants):
case 'error': return FAILURE_LEVEL   // 'failure' / ANNOTATION_FAILURE
case 'warning': return WARNING_LEVEL
default: return NOTICE_LEVEL         // notice is the catch-all
```
```ts
const MAX_ANNOTATIONS = 50
if (problems.annotations.length >= MAX_ANNOTATIONS) {
  for (let i = 0; i < problems.annotations.length; i += MAX_ANNOTATIONS) {
    await publishGitHubCheck(failedByThreshold, name, {..., annotations: problems.annotations.slice(i, i + MAX_ANNOTATIONS)})
  }
}
```

**Flow:** read SARIF → build rule-id→description map (driver + extensions) → filter `baselineState ∈ {unchanged, absent}` OUT (only new problems surface) → drop results without `locations[0].physicalLocation` (null-safe skip) → map each to the platform shape: GitHub annotation carries path/lines/columns (`start_column/end_column only when startLine === endColumn` quirk preserved verbatim :141-144), markdown descriptor carries title+level → publish: ≥50 annotations are sent in slices of 50 as separate check-update calls; on Checks-API failure (missing `checks: write`) fall back to per-problem `core.error/warning/notice` limited output.
**Invariant:** Title counting uses the FILTERED length ("N new problems found by <tool driver fullName|Qodana>") — the same number shown in the summary table; the conclusion ladder is failure-if-threshold ELSE neutral-if-any-annotation-of-any-level ELSE success (`getGitHubCheckConclusion` :200-216) — note ANY finding makes the check neutral, not failed; only failThreshold or zero findings decide success/failure.
**Probe:** `scan/__tests__/main.test.ts` :95-131 — parseSarif over `__tests__/data/some.sarif.json` + `with.baseline.sarif.json` (baseline file yields SAME new-problem set = the filter's whole point) + empty sarif; conclusion matrix failure/neutral/success; `toAnnotationProperties` round-trip. `common/__tests__/main.test.ts` :66-91 pins common-side parseSarif against fixtures.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qodana-action", query: "parseSarif baselineState annotations MAX_ANNOTATIONS", limit: 8 });
```

## Verdict
Adopt baseline-state filtering + three-level ladder + null-location skip + chunked check publishing for any SARIF-emitting tool integration; adapt target shapes (Checks API vs discussion threads); omit GitHub-specific fallback text but keep the degrade-don't-fail posture of publishAnnotations' catch block.
