<!-- capsule-v2 -->
# SARIF side-channel extraction — how do coverage numbers and sanity counts travel from report properties into the summary, and what happens when the file is missing?

**Source:** qodana-action Apache-2.0 `main@e0675fbe…`; Codebase Memory `qodana-action`. **Question:** SARIF carries non-problem metadata (test coverage, sanity results) beside `results[]`. How is that read, defaulted, and degraded — and why do the two extractors disagree on missing files?

## properties.* readers with opposite degradation contracts
**Path/Symbol:** `common/qodana.ts:getCoverageFromSarif` (:306-350), `getSanityProblemsCount` (:356-366), constants `COVERAGE_THRESHOLD=50` (:44); consumers all three `*/src/output.ts:publishOutput` (trace: 9 inbound rows — each main+output pair) feeding `getCoverageStats`/`getSanityWarning` (markdown-report-assembly).
**Signature:** `getCoverageFromSarif(sarifPath): Coverage` (THROWS when file absent) / `getSanityProblemsCount(sarifPath): number` (returns 0).
**Data Shape:** reads `runs[0].properties.coverage{total*,fresh*}` + thresholds from `runs[0].properties.qodanaFailureConditions.testCoverageThresholds.{totalCoverage,freshCoverage}`; sanity = length of `runs[0].properties['qodana.sanity.results']`.

### Decisive source
```ts
totalCoverageThreshold:
  sarifContents.runs[0].properties['qodanaFailureConditions']
    ?.['testCoverageThresholds']?.['totalCoverage'] || COVERAGE_THRESHOLD,   // default 50
// ...
return sarifContents.runs?.[0]?.properties?.['qodana.sanity.results']?.length ?? 0
// vs coverage's exit path:
throw new Error(`SARIF file not found: ${sarifPath}`)
```

**Flow:** publishOutput (every host) calls both extractors against `<resultsDir>/qodana.sarif.json` BEFORE composing the summary, so the summary pipeline stays a pure function of extracted values (getSummary takes `coverageInfo`/`sanityProblemsCount`, never paths). Missing `properties.coverage` zero-fills every field but still returns thresholds-defaulted Coverage; missing sanity property → 0; missing FILE → sanity 0, coverage THROW.
**Invariant:** The asymmetry is deliberate posture, not drift: a summary without coverage is still worth publishing (zero-fill keeps the section skippable via totalLines==totalCoveredLines==0 in getSummary), while a missing SARIF file means the whole run's premise failed — loud throw. Thresholds always come from the report itself with 50 as fallback, never per-host hardcoding.
**Probe:** EXECUTED at pin: common suite **62 passed**, incl. four `getCoverageStats(getCoverageFromSarif(...))` fixture tests :34-64 (`some.sarif.json`=pass vs `empty.sarif.json`=fail × diff/spam rendering through the REAL extractor) and three sanity tests :93-103 — `does.not.exist.json → 0` pins the degradation contract directly. scan/gitlab/vsts suites green same window.
**Coverage caveat:** none — cited paths no_recorded_issue, generation matches.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qodana-action", query: "getCoverageFromSarif getSanityProblemsCount coverage threshold sanity", limit: 6 });
```
(rank-1/rank-2 are the two extractors at execution time; vsts.QodanaScan rows are BUILD OUTPUT.)

## Verdict
Adopt side-channel readers that keep the renderer pure, SARIF-native thresholds with one global fallback, and per-side-channel degradation choice (fill-vs-throw by how load-bearing the datum is); adapt property names to your tool's schema; omit nothing — the asymmetry is the design.
