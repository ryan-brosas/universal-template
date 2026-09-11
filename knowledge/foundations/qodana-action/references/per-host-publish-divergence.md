<!-- capsule-v2 -->
# Per-host publish divergence — three `output.ts` twins that share 90% of their body and diverge in exactly four load-bearing places

**Source:** qodana-action Apache-2.0 `main@e0675fbe…` (pass 3 @ unchanged pin); Codebase Memory `qodana-action`. **Question:** Each adapter has its own `publishOutput` over the same shared `getSummary` pipeline — which differences are load-bearing contracts a porter must preserve, and which are cosmetic host mechanics?

## The divergence matrix: diff-vs-span rendering, comment gating, summary channel, error severity
**Path/Symbol:** `scan/src/output.ts:publishOutput` (:81-149), `gitlab/src/output.ts:publishOutput` (:38-93), `vsts/src/output.ts:publishOutput` (:63-122); bridge `annotationsToProblemDescriptors` (scan :151-171, converts GitHub `Annotation[]` BACK into common's `ProblemDescriptor[]` via the SAME failure/warning/notice ladder); limits `DEPENDENCY_CHARS_LIMIT` = 65000/65336/150000 (scan :53 / gitlab :18 / vsts :35).
**Signature:** all three: `publishOutput(projectDir, sourceDir, resultsDir, postComment, isPrMode, execute)` — EXCEPT scan adds leading `failedByThreshold: boolean` + `useAnnotations: boolean` (8 params vs 6).
**Data Shape:** input sidecars identical (`qodana.sarif.json`, `qodana-short.sarif.json`, license/report files); output = one markdown summary string + per-host delivery calls.

### Decisive source
```ts
// useDiffBlock argument — the ONLY call-site divergence of getCoverageStats:
const coverageInfo = getCoverageStats(
  getCoverageFromSarif(`${resultsDir}/${QODANA_SHORT_SARIF_NAME}`),
  true    // scan + gitlab: ```diff fences (+/- prefix)
  false   // vsts ALONE: HTML colored spans — Azure strips fenced diffs in summaries
)
```
```ts
// scan :127-141 — fan-out of FOUR deliveries incl. reaction swap + job summary:
await Promise.all([
  putReaction(getInputs().githubToken, ANALYSIS_FINISHED_REACTION, ANALYSIS_STARTED_REACTION),
  postResultsToPRComments(toolName, problems.summary, sourceDir, postComment),
  core.summary.addRaw(problems.summary).write(),          // GitHub-only channel
  publishAnnotations(jobName, problems, failedByThreshold, useAnnotations)
])
// gitlab :81 — PR-mode AND post-comment gate BEFORE any comment write:
if (isPrMode && postComment) { await postResultsToPRComments(toolName, sourceDir, problems.summary, problemsDescriptions.length != 0, postComment) }
// vsts :107-114 — summary ALWAYS written; comment NOT gated on prMode:
postSummary(problems.summary)
await postResultsToPRComments(toolName, sourceDir, problems.summary, problemsDescriptions.length != 0, postComment)
```
```ts
// error severity ladder for the SAME try/catch wrapper:
scan  :143  core.warning(`Qodana has problems with publishing results to GitHub – ${msg}`)
vsts  :116  tl.warning(`Qodana has problems with publishing results to Azure – ${msg}`)
gitlab:91   console.error((e as Error).message)   // bare stderr, no host API
```

**Flow:** every twin: skip silently when `execute=false` → parseSarif → getReportURL → sanity count → coverage stats → license info → derive toolName by splitting the shared title on `'found by '` (`:110/:66/:91`, falling back to `QODANA_CHECK_NAME`) → getSummary → deliver. The scan variant alone converts its richer annotation objects back into descriptors before summarizing (title-count parity with the Checks API is preserved because both count the SAME filtered set). GitLab is the only adapter whose COMMENT respects pr-mode (its MR-note model makes off-mode comments noise); Azure always posts thread comments but adds a separate always-on job-summary call; GitHub posts unconditionally too but fans out concurrently with annotations + reactions.
**Invariant:** `useDiffBlock` must match the HOST's markdown renderer, not taste: Azure DevOps renders neither ```diff fences nor `+/-` semantics, so vsts passes false while scan/gitlab pass true — porting the "wrong" twin's flag yields unreadable coverage blocks. The toolName split-on-`'found by '` is a hidden COUPLING between common's title grammar and every adapter — change the title template in `common/output.ts` and all three toolNames (comment tags, check names, monorepo suffixing `${toolName} (${sourceDir})`) break together. Publishing failures degrade to WARNINGS everywhere (never fail the job): analysis already happened; reporting is best-effort.
**Probe:** `grep -n 'true$' scan/src/output.ts | grep -c .` ≥1 with `sed -n '100,103p' scan/src/output.ts` showing `true`; `sed -n '83,86p' vsts/src/output.ts` showing `false`; `grep -n "split('found by ')" scan/src/output.ts gitlab/src/output.ts vsts/src/output.ts` → `110:`/`66:`/`91:`; `grep -n 'isPrMode && postComment' gitlab/src/output.ts` → `81:` (and ABSENT in scan/vsts); anchored at repo root.
**Runner evidence:** real jest at pin — `common` suite **62 passed** when filtered to `__tests__/main.test.ts` (`cd common && ../node_modules/.bin/jest --config jest.config.js __tests__/main.test.ts`, rc=0) incl. the four getCoverageStats diff/spam exact-string fixtures (:34-64), getReportURL describe (:105+), getNativeModePrefix (:197+), isMergeCommit (:215-248), full parseRawArguments table (:250-548); `scan` suite **11 passed** (`__tests__/main.test.ts`) incl. typical/empty summary fixtures driving `annotationsToProblemDescriptors(...).reverse()` through getSummary (:37-69). Full-suite runs hit `Unknown system error -122` (EDQUOT /tmp quota under fleet load) — environmental, not test failures; recorded honestly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qodana-action", query: "publishOutput summary coverage annotations", limit: 6 });
```
(rank order returns all FOUR publishOutputs line-exact — the three src twins PLUS the compiled bundle twin `vsts/QodanaScan/index.js` :81629+, which is build output, never cite it.)

## Verdict
Adopt the shared-pipeline + thin-per-host-delivery shape with an EXPLICIT divergence matrix (rendering mode per host markdown dialect, comment-gating policy per host surface model, extra channels per host, uniform warn-don't-fail posture); adapt channel names to your hosts. Omit nothing structural — the four divergences ARE the porting contract; everything else is deliberately identical so reviewers diff twins against drift.
