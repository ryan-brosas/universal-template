<!-- capsule-v2 -->
# File-source overlay — how do extraction stages reuse bytes the hash pass already read without pinning the whole repo in memory?

**Source:** pi-fovea MIT `main@5bd4e6f5c56190fb174245266464607b11f7a337`; Codebase Memory `mnt-hdd-utopia-inspo-pi-fovea`. **Question:** A multi-stage extractor (hash pass, then symbol/call/literal/anchor passes) would read every dirty file twice — or, if it caches everything, hold the entire repo's text in memory at once. What is the seam that reuses hot bytes and lazily re-reads the rest?

## Pre-seeded overlay + per-file single-flight + never-throw reads
**Path/Symbol:** `src/core/source.ts:FileSource/makeFileSource/readAll` (:9-44); seeding policy `src/core/build.ts:makeTextBudget/TEXT_RETAIN_TOTAL/TEXT_RETAIN_FILE` (:254-263); consumers `src/core/build.ts:extractInto` (:498), `runAnchorPass`, `src/core/anchors.ts:extractFileRoutes`.
**Signature:** `makeFileSource(root: string, contents?: ReadonlyMap<string, string>): FileSource`; `FileSource.read(file): Promise<string | undefined>`; `readAll(files: readonly string[], source: FileSource): Promise<Map<string, string>>`.
**Data Shape:** `contents` maps repo-relative path → already-read UTF-8 text (the bounded prefetch window); the inflight map holds `path → Promise<string|undefined>` only while a read is in flight; `readAll`'s result map contains ONLY readable files (presence == readable).

### Decisive source
```ts
// build.ts — WHY the overlay is bounded, not "cache everything":
// Hash passes touch every dirty file; holding every text until extraction
// ends means a large root pins ALL of its source in memory at once (one
// such probe OOM-killed the host). Keep a bounded prefetch window instead:
// files past the budget are lazily re-read by FileSource where extraction
// actually needs content, and spent texts drop with the pass.
const TEXT_RETAIN_TOTAL = 16 * 1024 * 1024;
const TEXT_RETAIN_FILE  = 128 * 1024;
const makeTextBudget = () => {
  let used = 0;
  return (rel: string, text: string, into: Map<string, string>): void => {
    if (text.length > TEXT_RETAIN_FILE || used + text.length > TEXT_RETAIN_TOTAL) return;
    into.set(rel, text);
    used += text.length;
  };
};
```
```ts
// source.ts — the three-layer read policy:
read(file) {
  const cached = contents?.get(file);
  if (cached !== undefined) return Promise.resolve(cached); // overlay wins
  const pending = inflight.get(file);
  if (pending) return pending;                              // single-flight
  const p = readFile(join(root, file), "utf8").then(
    (text) => text,
    () => undefined,                                        // never throws
  ).finally(() => inflight.delete(file));                   // self-cleaning
  inflight.set(file, p);
  return p;
}
```

**Flow:** loadFacts hashes every dirty file and admits small ones into a bounded prefetch map (`makeTextBudget`) → `extractInto` hands that map to `makeFileSource(root, contents)` → symbol/scan/route passes all call `source.read` concurrently: hot files resolve instantly from the overlay, cold/large files coalesce into ONE disk read each via the inflight map → unreadable paths yield `undefined`, which callers treat as "skip honestly" rather than an error.
**Invariant:** The overlay is authoritative for its keys — extraction MUST see exactly the bytes that were hashed, even if the file changes on disk mid-pass (hash/fact consistency). Memory safety lives UPSTREAM in the budget function; correctness (single-flight, no-throw) lives in the source. Inflight entries delete themselves in `.finally`, so neither resolved values nor failures are cached — every pass re-reads cold files fresh. A missing/unreadable file is `undefined`, never a thrown error crossing extraction stages.
**Probe:** No direct test imports `source.ts` (coverage caveat — recorded honestly); behavior is exercised indirectly through `tests/extract.test.ts` / `tests/ops.test.ts`, which run `extractInto`→`makeFileSource` end-to-end over the `tests/fixtures/mini` corpus and assert extracted facts. Deterministic probe this pass: full suite GREEN (160/160 on runs 2–3; see ownership-lattice erratum for run 1's unrelated provenance flake).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-fovea", file_pattern: "core/source.ts", query: "source", limit: 10, fields: ["lines", "signature"] });
// → src.core.source.makeFileSource :15-31, .read :18-29, .readAll :34-44, FileSource :9-12
```
Executed live this pass on generation 2026-08-25T08:39:46Z @ head 5bd4e6f5c561; `check_index_coverage("src/core/source.ts")` = no_recorded_issue/metadata_match.

## Verdict
Adopt the split-brain pairing — bounded prefetch budget in the caller + single-flight no-throw faucet in the provider — anywhere a hashing/validation pass precedes content-consuming passes over the same files. Adapt the 16 MiB/128 KiB constants to your memory envelope and average file size. Omit nothing: dropping the inflight layer silently doubles disk reads under concurrent passes; caching resolved values instead of promises would serve stale text after mid-pass edits.
