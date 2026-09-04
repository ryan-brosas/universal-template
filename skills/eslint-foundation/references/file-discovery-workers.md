<!-- capsule-v2 -->
# File discovery + worker scaling — how are glob patterns turned into a deduped file list, and when does linting fan out to worker threads?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** How do you resolve mixed file/directory/glob patterns and decide single-thread vs worker execution?

## findFiles pattern partitioning
**Path/Symbol:** `lib/eslint/eslint-helpers.js:findFiles` (:518–640) + `globSearch` (:261–384).
**Signature:** `findFiles({ patterns, globInputPaths, cwd, configLoader, errorOnUnmatchedPattern }): Promise<string[]>`.
**Data Shape:** searches grouped per base path in a `Map<basePath, {patterns, rawPatterns}>`; direct files bypass globs entirely; unmatched non-glob paths collect into `missingPatterns` (error if `errorOnUnmatchedPattern`).

### Decisive source
```js
// stat each pattern; only non-existent ones can be globs:
if (stat) {
  if (stat.isFile()) { results.push(filePath); promises.push(configLoader.loadConfigArrayForFile(filePath)); }
  if (stat.isDirectory()) { /* group under dir */ globbyPatterns.push(`${normalizeToPosix(filePath)}/**`); }
  return;
}
if (globInputPaths && isGlobPattern(pattern)) {
  const basePath = path.resolve(cwd, globParent(pattern));   // group by glob parent
  // ...
}
return [...new Set([...results, ...globbyResults])];          // dedupe
```

**Flow:** stat all patterns → existing files go straight to results (+config preload), directories expand to `dir/**`, real globs group under `globParent` → parallel `globSearch` walks with minimatch (`dot:true`), consulting the ConfigLoader so ignoring is decided by the *same* flat-config logic as linting → union+dedupe.
**Invariant:** ignore decisions during discovery come from `configs.isDirectoryIgnored/getConfig`, never from the glob matcher alone — a separate ignore implementation would disagree with the linter. Unmatched-pattern errors distinguish "no files at all" (`NoFilesFoundError`) from "matched but ignored" (`AllFilesIgnoredError`, found via a second ignore-free `globMatch` probe). The unmatched set is only pruned when the matched file also has a config.
**Probe:** `tests/lib/eslint/eslint.js:2683-2714` ("should always throw an error for the first unmatched file pattern") asserts both error classes and their precedence: unmatched-glob-first ⇒ `/No files matching 'doesnotexist1\/\*\.js' were found/`; mixed matched-ignored + unmatched ⇒ still NoFilesFound; ignored-only patterns ⇒ `/All files matched by 'subdir1\/\*\.js' are ignored/` regardless of pair order. ERRATUM (pass 6 verification, 2026-08-24): earlier probe cited `tests/lib/eslint/eslint-helpers.js`, which does NOT exist at pin `c27bc92e` — the behavior lives in eslint.js only.

## Worker-count decision
**Path/Symbol:** `lib/eslint/eslint.js:calculateWorkerCount` (:410–428) + `getWorkerCountFor` (:309–318) + `calculateAutoWorkerCount` (:347–401).
**Signature:** `calculateWorkerCount(eslint, filePaths): number` — module-exported so tests can stub it.

### Decisive source
```js
function getWorkerCountFor(processableFileCount, maxWorkers) {
  let workerCount = Math.ceil(processableFileCount / AUTO_FILES_PER_WORKER);  // 50 files/worker
  if (workerCount > maxWorkers) workerCount = maxWorkers;
  if (workerCount <= 1) return 0;                    // 1 worker == just run inline
  return workerCount;
}
// concurrency: "off" -> 0; "auto" -> ceil(files/50) capped at cores>>1, counting only
// files that actually need reprocessing (cache-aware early-exit loop); numeric N -> min(N, files)
```

**Flow:** `concurrency:"off"` ⇒ 0 ⇒ `lintFilesWithoutMultithreading` (Promise.all reads + Retrier on ENFILE/EMFILE); `"auto"` ⇒ count processable files (skipping validly cached ones unless fixing) with an early-break once more files can't raise the worker count; numeric ⇒ clamp. Workers share one `SharedArrayBuffer` file-index counter, results return index-tagged, any worker error aborts the rest via one AbortController, and low "net linting ratio" (<0.7) warns that threading didn't pay off. Cache persists after results settle (`reconcile()`), never mid-flight.
**Invariant:** workerCount ≤1 collapses to single-thread — spawning exactly one worker is pure overhead. In multithread mode options must be structured-cloneable or supplied as a module URL (`ESLINT_UNCLONEABLE_OPTIONS`).
**Probe:** `tests/lib/eslint/eslint.js` (calculateWorkerCount override hook, empty-pattern collapse: `""`/`[]` → `"."` unless `passOnNoPatterns`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "findFiles globSearch calculateWorkerCount", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.eslint.eslint.calculateWorkerCount" });
```

## Verdict
Adopt stat-first pattern partitioning, config-loader-driven ignore filtering during walk, cache-aware auto worker sizing, and the ≤1-worker→inline rule; adapt the 50-files/worker heuristic, net-linting-ratio threshold, and retry codes to host; omit ESLint's suppressions service and options-module indirection unless porting the full CLI surface.
