<!-- capsule-v2 -->
# CLI spawn retry on ENOENT — how do you survive a self-updating CLI backend without mistaking real failures for transient ones?

**Source:** veda MIT `master@f050518c99fa54a5a0af4a04918aaf01d1ed94e1`; Codebase Memory `veda`. **Question:** Which spawn failures are retryable, what bounds the retries, and how is NDJSON streamed back?

## isSpawnEnoent → computeBackoffMs → spawnCliWithRetry → parseNdjsonStream
**Path/Symbol:** `src/backend/util/spawn.ts:isSpawnEnoent` (:26-42), `computeBackoffMs` (:44-62), `spawnCli` (:68-98), `spawnCliWithRetry` (:106-154), `commandExists` (:156-167), `parseNdjsonStream` (:169-202).
**Signature:** `spawnCliWithRetry(options: SpawnOptions, retryOptions?: RetryOptions): Promise<SpawnResult>`; defaults `{maxAttempts: 6, maxTotalMs: 15000, baseDelayMs: 250, maxDelayMs: 2000, jitter: true}`.
**Data Shape:** `RetryOptions {maxAttempts?, baseDelayMs?, maxDelayMs?, maxTotalMs?, jitter?, onRetry?(attempt, error, delayMs)}`; delay = `min(base·2^attempt, max)` × uniform 0.8-1.2 jitter.

### Decisive source
```ts
// Check if this is an ENOENT error (retryable)
if (!isSpawnEnoent(error)) {
  throw error;   // non-ENOENT fails IMMEDIATELY
}
...
if (elapsed >= maxTotalMs) {
  throw new Error(
    `Failed to spawn "${options.command}" after ${attempt} attempt(s) ` +
    `over ${Math.round(elapsed)}ms. The CLI may be updating or not installed. ` +
    ...
```

**Flow:** classify FIRST — only ENOENT (Bun `error.code`, or message containing "Executable not found"/"ENOENT") retries, because self-updating CLIs (e.g. Gemini) momentarily vanish from PATH mid-binary-swap; anything else propagates untouched → exponential backoff with ±20% jitter, hard wall-clock budget checked BEFORE sleeping → final error names attempts + elapsed + cause → stdout consumed as async-generator NDJSON: split('\n'), pop() keeps the partial tail in buffer, malformed lines SKIPPED not thrown, trailing buffered line still parsed at stream end.
**Invariant:** Retry classification must precede backoff (retrying non-transient errors masks real breakage); the time budget dominates attempt count (6 attempts can exhaust early); NDJSON parsing never throws on bad lines — silent skip is the contract for mixed stderr noise.
**Probe:** `tests/backend/transient-errors.test.ts` (:9-35 isSpawnEnoent ×5 incl. null/non-object payloads, :36-88 backoff/jitter/caps/sleep, :89+ codex/claude transient-message filters with does-not-filter-real-errors counterweights) — EXECUTED this pass: 20 pass / 0 fail at HEAD.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-ecosystem-veda", query: "spawnCliWithRetry isSpawnEnoent computeBackoffMs", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt classify-then-retry with wall-clock budgets and lenient NDJSON streaming for any CLI-driven backend. Adapt detection strings to your runtime's ENOENT shapes. Omit Bun-specific Subprocess typing if porting to node child_process.
