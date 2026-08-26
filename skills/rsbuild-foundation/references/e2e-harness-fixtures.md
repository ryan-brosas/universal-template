<!-- capsule-v2 -->
# E2E harness fixtures — why does copySrcDir exist and devOnly/buildPreview split the server lifecycle?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter building bundler-e2e harnesses must reproduce the fixture-isolation and lifecycle-splitting helpers.

## Connected graph-selected seam
**Path/Symbol:** `e2e/helper.ts` + `@scripts/test-helper` (matchRules/matchPlugin) — fixture API `{build, dev, devOnly, buildPreview, page, gotoPage, editFile, copySrcDir, expectLog, clearLogs, expectNoLog}` as consumed across e2e/cases (see manifest/basic:4 `getFileContent(files,'manifest.json')`, browser-logs/dedupe-log:3 `copySrcDir()+editFile`).
**Signature:** `test('...', async ({ devOnly, page, editFile, copySrcDir }) => ...)`.
**Data Shape:** dist files exposed as a map for content assertions; logs accumulated server-side and cleared between phases.

### Decisive source
```ts
// usage pattern pinned across suites:
const tempSrc = await copySrcDir();          // clone the case's src/ into a temp dir → edits never touch the repo
await gotoPage(page, rsbuild, '/', { hash: 'test1' });
await rsbuild.expectLog('Error: value is #test1');
rsbuild.clearLogs();                          // phase separation so stale logs can't satisfy later assertions
```
```ts
test('should generate manifest file in output', async ({ build }) => { ... });       // prod build only
test('should not generate integrity attributes in dev', async ({ ... }) => { ... }); // dev vs preview vs build split per suite
```

**Flow:** devOnly boots ONLY the dev server (no prior prod build); buildPreview builds then serves dist; build runs compilation without serving. Log expectations poll an internal buffer rather than scraping stdout — deterministic under parallel workers. HMR assertions use editFile against the COPIED src then await recompile via log/page signals.
**Invariant:** (1) every mutating test must go through copySrcDir or concurrent workers corrupt sibling cases; (2) expectLog/clearLogs pairing is what makes multi-phase tests order-independent; (3) getFileContent-style helpers read from the in-memory dist map — no disk dependency when writeToDisk is false.
**Probe:** the harness itself is the probe surface: e2e/cases/**/index.test.ts (~200 suites) exercise it; unit coverage N/A by design.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "copySrcDir editFile expectLog buildPreview devOnly", limit: 8 });
```

## Verdict
Adopt fixture cloning, lifecycle-splitting fixtures, buffered log assertions, and in-memory dist inspection. Adapt to host test runner. Omit framework-specific page helpers.
