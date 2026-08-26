<!-- capsule-v2 -->
# Markdown report assembly — how do you render a bounded, monorepo-aware summary that degrades when there is no cloud URL?

**Source:** qodana-action Apache-2.0 `main@829c6a56…`; Codebase Memory `qodana-action`. **Question:** How is the PR comment / job summary composed, what bounds it to platform limits, and how do coverage and licenses fold in?

## getSummary section pipeline + char-limit gating + tag-based comment upsert
**Path/Symbol:** `common/output.ts:getSummary` (:272-363), `getRowsByLevel` (:240-255 count-sorted table rows), `makeConclusion` (:138-150 diff +/- vs colored span), `getCoverageStats` (:152-177), `getLicenseInfo` (:179-198), `getReportURL` (:200-215), `wrapToToggleBlock` (:217-223), `getViewReportText` (:225-233), `getSanityWarning` (:385-395), plurals (:370-404), `getCommentTag` (:406-409); per-platform limits `scan DEPENDENCY_CHARS_LIMIT=65000` / `gitlab 65336` / `vsts 150000`.
**Signature:** `getSummary(toolName, projectDir, sourceDir, descriptors[], coverageInfo, packages, licensesInfo, reportUrl, prMode, dependencyCharsLimit, reportViewOptionsHelp, sanityProblemsCount=0): string`.
**Data Shape:** Input = parsed problems + sidecar files in resultsDir (`qodana.sarif.json`, `qodana-short.sarif.json`, `qodana.cloud`, `open-in-ide.json`, `projectStructure/third-party-libraries.json|.md`).

### Decisive source
```ts
let licensesBlock = ''
if (licensesInfo !== '' && licensesInfo.length < dependencyCharsLimit) {
  licensesBlock = wrapToToggleBlock(`Detected ${packages} ${getDepencencyPlural(packages)}`, licensesInfo)
}
...
if (reportUrl !== '') {
  const firstToolName = toolName.split(' ')[0]
  toolName = toolName.replace(firstToolName, `[${firstToolName}](${reportUrl})`)
}
```

**Flow:** header (# toolName, first word linkified when a report URL exists) → analysis scope lines (projectDir/sourceDir, omitted when empty — sourceDir distinguishes monorepo projects) → either "**It seems all right 👌**" empty-path or the problems table: per-level groups (🔴 Failure / 🔶 Warning / ◽️ Notice), rows sorted by count descending, unknown-rule fallback `` `Unknown` `` → optional sanity-problems warning (⚠️ N sanity problems… misconfigured-project hint, links the report or plain word when no URL) → coverage block: `@@ Code coverage @@` header, total + fresh lines each wrapped by makeConclusion (diff-mode `+/-` prefix inside a ```diff fence vs HTML colored spans), skipped entirely when both totalLines and totalCoveredLines are 0 → PR-mode note → view-report section: ☁️ link when URL known else a `<details>` toggle listing setup options (per-platform help text constant) → licenses `<details>` ONLY if non-empty AND under the platform char limit → contact toggle. Comment identity: `<!-- JetBrains/qodana-action@v${VERSION} : ${toolName}, ${sourceDir} -->` appended to every posted body so the next run can find-and-update instead of re-posting (monorepo-safe via toolName+sourceDir keying).
**Invariant:** The license block is DROPPED SILENTLY (no truncation!) when it exceeds the limit — a porter must not "fix" this by clipping: partial license lists misrepresent legal state. Coverage thresholds come from SARIF `properties.qodanaFailureConditions.testCoverageThresholds` with default 50 (`COVERAGE_THRESHOLD`), never hardcoded per platform.
**Probe:** `common/__tests__/main.test.ts` :34-64 four getCoverageStats fixture tests (pass/fail × diff/spam exact strings); `scan/__tests__/main.test.ts` :37-69 typical + empty summary exact-markdown fixtures incl. reversed input array proving count-sort; `gitlab/vsts __tests__` mirror the summary fixtures with their own VIEW_REPORT_OPTIONS and limits.
**Coverage caveat:** postResultsToPRComments network paths untested upstream; pinned via ranges (scan/src/utils.ts:507-603).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qodana-action", query: "getSummary wrapToToggleBlock coverage licenses", limit: 8 });
```

## Verdict
Adopt the section pipeline, the silent-drop-over-truncate license rule, the dual rendering mode (diff fences for PR comments, HTML spans for summaries), and the hidden-tag comment-upsert identity scheme; adapt limits and help text per host; omit nothing structural.
