<!-- capsule-v2 -->
# Server-Side Hotfix Channel — how do you disable a broken feature in production WITHOUT shipping a new extension build?

**Source:** refined-github MIT `main@3bbe6088fe301d0d5cf1ae751a49307005762a68`; Codebase Memory `refined-github`. **Question:** What is the CSV hotfix format, its version filtering, cache policy, and the sync-strings side channel?

## Connected graph-selected seam
**Path/Symbol:** `source/helpers/hotfix.tsx:` `brokenFeatures` (:130–143), `styleHotfixes` (:145–154), `brokenFeaturesAsOptions` (:156–166), `_` string hook (:177–181), `preloadSyncLocalStrings` (:193–199); parser `source/helpers/hotfix-parse.ts:parseBrokenFeaturesCsv` (:204–219); fetcher `fetchHotfix` (:121–126).
**Signature:** `parseBrokenFeaturesCsv(content: string, currentVersion: string): [featureId, relatedIssue, unaffectedVersion][]`; `brokenFeaturesAsOptions(storage?): Partial<RghOptions>`.
**Data Shape:** GitHub-Pages-hosted CSV (NOT the rate-limited API), header row skipped; row = `featureId,issueUrl,unaffectedVersion` (third column optional). Cache: 6h fresh / 30d stale-while-revalidate (`CachedFunction`). Style hotfixes: per-version CSS file with same 6h TTL but **300-day** SWR and single-key cache.

### Decisive source
```ts
// A broken feature stays disabled only while the installed version is NEWER than
// the last-known-good version — old rows auto-expire for old installs:
if (featureId && relatedIssue && (!unaffectedVersion || compareVersions(unaffectedVersion, currentVersion) > 0)) {
	entries.push([featureId, relatedIssue, unrelatedVersion]);
}
```
```ts
// Boot merges hotfixes INTO the options object before any feature reads it:
Object.assign(options, brokenFeaturesAsOptions(localHotfixes)); // cached-first
void brokenFeatures.get();                                      // revalidate async
```

**Flow:** content-script boot → `Promise.all([options, toggle, brokenFeatures.getCached(), bisect, preloadStrings])` → if bisect active it WINS over hotfixes; else cached broken list is merged as `feature:<id>: false` options while the fresh fetch happens unawaited → feature-manager's normal disable path takes over. Style hotfixes travel a different route: background-page message (`getStyleHotfixes`) → `<style>` PREPENDED TO `<body>` (only guaranteed position after static CSS) unless GHE. Strings hotfix (`strings.json`) preloads into a module-local map so the `_` tagged-template can substitute synchronously at render time.
**Invariant:** version gate uses `>` against the UNAFFECTED version — an entry pins "broken from X onward" semantics and must not disable features on versions older than the regression. Dev builds skip ALL hotfix fetching (`isDevelopmentVersion()`) or debugging becomes impossible. The `_()` substitution must be populated BEFORE components render (hence boot-time preload into a local, never awaited at use time).
**Probe:** `source/helpers/hotfix-parse.test.ts` pins the CSV parse + version comparison directly (rows incl. empty/absent third column); merge-order and dev-skip are source-cited (refined-github.ts :128–136). Coverage caveat: CachedFunction network behavior untested.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", query: "brokenFeatures styleHotfixes parseBrokenFeaturesCsv hotfix", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the whole channel for any shipped-but-editable product needing post-release kill switches: static-host CSV, version-gated rows, cached-merge-at-boot, dev bypass. Adapt TTLs, host, and row schema. Omit the strings/style variants unless you ship UI copy/CSS that can regress server-side. Direct test covers the parser; caching/boot wiring caveat-recorded.
