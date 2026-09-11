<!-- capsule-v2 -->
# Worker file-claim loop — how do N worker threads share one file list without a broker?

**Source:** ESLint MIT `main@c27bc926e496985eb7911c09eb60914b2e4b5d0f`; Codebase Memory project `eslint`. **Question:** How do you distribute a fixed file list across a pool of worker threads with zero coordination messages, and how do out-of-order completions come back in original file order?

## Atomics counter claim loop + indexed result reassembly
**Path/Symbol:** `lib/eslint/worker.js` (whole file, :1–173): `workerData` contract (:40–46 typedef, :71 destructure), options-or-URL consumption (:72–76), no-op warnings (:80–82), claim loop (:115–157), netLintingDuration (:159–166), postMessage (:172); main side `lib/eslint/eslint.js:runWorkers` (:456–545: SharedArrayBuffer setup :465–467, workerOptions/env :470–477, indexed reassembly :509–513).
**Signature:** workerData = `{ eslintOptionsOrURL: ESLintOptions | string, filePathIndexArray: Uint32Array<SharedArrayBuffer>, filePaths: string[] }`; worker posts `IndexedLintResult[] & { netLintingDuration: bigint, timings? }`.
**Data Shape:** ONE 4-byte shared counter (`new Uint32Array(new SharedArrayBuffer(4))`) plus the full path array shipped once at spawn; no per-file messages either direction; `env: SHARE_ENV` makes process.env bidirectionally live between controlling thread and workers.

### Decisive source
```js
// worker side — claim the next file with an atomic increment; stop when past the end:
for (;;) {
  const index = Atomics.add(filePathIndexArray, 0, 1);
  const filePath = filePaths[index];
  if (!filePath) break;
  ...
  const result = await lintFile(filePath, configs, processedESLintOptions, linter, lintResultCache, readFileCounter);
  if (result) { result.index = index; indexedResults.push(result); }
}
// main side — preallocate in original order, slot by claimed index, strip the tag:
const results = Array(fileCount);
for (const result of indexedResults) {
  const { index } = result;
  delete result.index;
  results[index] = result;
}
```

**Flow:** main builds counter+paths+options-or-URL → spawns N workers → each worker loops `Atomics.add` → undefined path ⇒ pool drained, break → worker times config-load and file-read separately (bigint accumulators) → posts one message with ALL its results tagged by claimed index → main slots them into a preallocated array, deletes the tag, resolves that worker's promise → `Promise.all` over workers.
**Invariant:** work distribution is lock-free and exactly-once (atomic increment is the only synchronization point; overflow deemed unreachable, source comment :118); completion order is irrelevant because the claimed index IS the output position — a failed worker leaves permanent null holes that the caller filters (`results.filter(result => !!result)` in lintFiles). Workers NO-OP `emitEmptyConfigWarning`/`emitInactiveFlagWarning` (controlling thread owns those warnings, :80–82) and disable timing display (:65); per-worker timings ride back on the results array and merge additively in main (:505–507). Options consumption discriminates `typeof === "object"` (raw cloneable options) vs string (module URL → `(await import(url)).default`, helpers :989–991) — see constructor-options-or-url-duality.
**Probe:** `tests/lib/eslint/eslint.js` (:9214–9273 "Environment sharing in multithread mode" — SHARE_ENV propagation pinned BOTH directions through a data-URL options module with concurrency 2; :12932–13139 calculateWorkerCount truth table incl. numeric 1⇒0, auto cores/2 cap, ignored-file exclusion, metadata-vs-content cache counting). Live probe this pass: `ESLint.fromOptionsModule(data URL)` + `concurrency: 2` over 2 files returned both results in original file order (a.js,b.js) despite parallel workers.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "worker.js workerData Atomics filePathIndexArray IndexedLintResult", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.eslint.worker" });
```

## Verdict
Adopt the atomic-counter claim loop + index-tagged reassembly whenever a host needs a brokerless fixed-workload pool: one 4-byte SharedArrayBuffer, one postMessage per worker, preallocated result array. Adapt the options transport (object-vs-URL duality is ESLint-specific) and the warning/timing ownership split to your host's service model. Omit the compile-cache enablement (`enableCompileCache?.()`, :13) unless your runtime has it. Caveat: Codebase Memory MCP was not connected in the mining session; anchors verified by direct byte-matched source reads at the git-clean pin.
